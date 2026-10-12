from unittest import mock

import pytest
import requests

from citeverify.clients.http import (
    HttpClient, HttpError, JsonFileCache, MemoryCache, OfflineCacheMiss, cache_key,
)


def fake_response(status=200, payload=None, text=None, headers=None):
    r = mock.Mock()
    r.status_code = status
    r.headers = headers or {}
    r.json.return_value = payload
    r.text = text if text is not None else ""
    return r


def client(*responses, **kw):
    session = mock.Mock()
    session.headers = {}
    session.get.side_effect = list(responses)
    sleeps = []
    c = HttpClient(session=session, sleep=sleeps.append, **kw)
    return c, session, sleeps


def test_cache_key_sorts_params():
    assert cache_key("u", {"b": 2, "a": 1}) == cache_key("u", {"a": 1, "b": 2}) == "u?a=1&b=2"
    assert cache_key("u") == "u"


def test_successful_response_is_cached():
    c, session, _ = client(fake_response(200, {"x": 1}))
    assert c.get("https://api.test/x").data == {"x": 1}
    assert c.get("https://api.test/x").data == {"x": 1}
    assert session.get.call_count == 1


def test_slim_is_applied_before_caching():
    c, _, _ = client(fake_response(200, {"keep": 1, "drop": 2}))
    r = c.get("https://api.test/x", slim=lambda d: {"keep": d["keep"]})
    assert r.data == {"keep": 1}
    assert c.cache.get("https://api.test/x")["data"] == {"keep": 1}


def test_404_is_cached_but_5xx_is_not():
    c, session, _ = client(fake_response(404), fake_response(503), fake_response(503), fake_response(503), retries=2)
    assert c.get("https://api.test/missing").status == 404
    assert c.get("https://api.test/missing").status == 404
    assert c.get("https://api.test/flaky").status == 503
    assert c.cache.get("https://api.test/flaky") is None
    assert session.get.call_count == 4


def test_retries_transient_errors_with_backoff():
    c, session, sleeps = client(
        requests.ConnectionError("down"), fake_response(503), fake_response(200, {"ok": True}),
        retries=2, backoff=0.5,
    )
    assert c.get("https://api.test/x").data == {"ok": True}
    assert session.get.call_count == 3
    assert sleeps == [0.5, 1.0]


def test_honours_retry_after():
    c, _, sleeps = client(fake_response(429, headers={"Retry-After": "2"}), fake_response(200, {}), retries=1)
    assert c.get("https://api.test/x").ok
    assert sleeps == [2.0]


def test_gives_up_with_http_error():
    c, session, _ = client(requests.Timeout(), requests.Timeout(), retries=1)
    with pytest.raises(HttpError):
        c.get("https://api.test/x")
    assert session.get.call_count == 2


def test_invalid_json_raises_http_error():
    bad = fake_response(200)
    bad.json.side_effect = ValueError("no json")
    c, _, _ = client(bad)
    with pytest.raises(HttpError):
        c.get("https://api.test/x")


def test_text_responses():
    c, _, _ = client(fake_response(200, text="<feed/>"))
    assert c.get("https://api.test/x", as_json=False).data == "<feed/>"


def test_offline_mode_never_touches_the_network():
    c, session, _ = client(offline=True)
    with pytest.raises(OfflineCacheMiss):
        c.get("https://api.test/x")
    session.get.assert_not_called()
    c.cache.set("https://api.test/x", {"status": 200, "data": 5})
    assert c.get("https://api.test/x").data == 5


def test_per_host_pacing():
    c, _, sleeps = client(fake_response(200, {}), fake_response(200, {}),
                          min_interval={"slow.test": 3.0})
    c.get("https://slow.test/a")
    c.get("https://slow.test/b")
    assert len(sleeps) == 1 and 0 < sleeps[0] <= 3.0


def test_memory_cache_evicts_oldest():
    m = MemoryCache(maxsize=2)
    m.set("a", {"v": 1}); m.set("b", {"v": 2}); m.get("a"); m.set("c", {"v": 3})
    assert m.get("b") is None and m.get("a") and m.get("c")


def test_json_file_cache_round_trip(tmp_path):
    path = tmp_path / "cache.json"
    cache = JsonFileCache(path)
    cache.set("k", {"status": 200, "data": {"t": "Ünïcode"}})
    assert cache.dirty
    cache.save()
    again = JsonFileCache(path)
    assert again.get("k") == {"status": 200, "data": {"t": "Ünïcode"}} and len(again) == 1
