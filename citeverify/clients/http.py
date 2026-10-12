"""HTTP layer shared by the registry clients: timeouts, retries, rate limiting, caching.

The cache is what makes evaluation reproducible: a :class:`JsonFileCache` recorded once
against the live APIs can be replayed offline (``HttpClient(offline=True)``), in which
case any request that is not in the cache raises :class:`OfflineCacheMiss` instead of
touching the network.
"""
from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol
from urllib.parse import urlencode, urlsplit

import requests

USER_AGENT = "CiteVerify/2.0 (+https://github.com/Shivani-Radhakrishnan/CiteVerify)"

#: Responses with these status codes are retried with backoff.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def is_cacheable(status: int) -> bool:
    """Success and client errors are definitive answers; 429 and 5xx are transient."""
    return status < 500 and status not in RETRY_STATUS


class HttpError(Exception):
    """A request could not be completed (network failure, timeout, bad payload)."""


class OfflineCacheMiss(HttpError):
    """Offline mode is on and the request is not in the cache."""


@dataclass(frozen=True)
class Response:
    """A minimal, cacheable HTTP response. ``data`` is parsed JSON or raw text."""

    status: int
    data: Any

    @property
    def ok(self) -> bool:
        return self.status == 200


class ResponseCache(Protocol):
    def get(self, key: str) -> Optional[dict]: ...

    def set(self, key: str, value: dict) -> None: ...


class MemoryCache:
    """Thread-safe in-process LRU cache."""

    def __init__(self, maxsize: int = 2048) -> None:
        self.maxsize = maxsize
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def set(self, key: str, value: dict) -> None:
        with self._lock:
            self._data[key] = value
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)


class JsonFileCache:
    """A cache persisted as a single, diff-friendly JSON file (used for recorded fixtures)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        self.dirty = False

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list[str]:
        return list(self._data)

    def get(self, key: str) -> Optional[dict]:
        return self._data.get(key)

    def set(self, key: str, value: dict) -> None:
        with self._lock:
            self._data[key] = value
            self.dirty = True

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self._data, indent=1, sort_keys=True, ensure_ascii=False)
            self.path.write_text(text + "\n", encoding="utf-8")
            self.dirty = False


def cache_key(url: str, params: Optional[Mapping[str, Any]] = None) -> str:
    """Stable key for a GET request: the URL plus its query parameters in sorted order."""
    if not params:
        return url
    return f"{url}?{urlencode(sorted((k, str(v)) for k, v in params.items()))}"


class HttpClient:
    """GET-only HTTP client with timeouts, retries/backoff, per-host pacing and caching.

    Args:
        timeout: per-request timeout in seconds.
        retries: extra attempts after a connection error, timeout or 429/5xx response.
        backoff: base delay in seconds; attempt ``n`` waits ``backoff * 2**n``.
        cache: response cache (defaults to an in-memory LRU).
        offline: never touch the network; cache misses raise :class:`OfflineCacheMiss`.
        min_interval: minimum seconds between requests to a host (e.g. arXiv asks for 3s).
        session: optional pre-configured :class:`requests.Session`.
        sleep: injectable sleep function (tests pass a no-op).
    """

    def __init__(
        self,
        *,
        timeout: float = 8.0,
        retries: int = 2,
        backoff: float = 0.5,
        cache: Optional[ResponseCache] = None,
        offline: bool = False,
        min_interval: Optional[Mapping[str, float]] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.cache: ResponseCache = cache if cache is not None else MemoryCache()
        self.offline = offline
        self.min_interval = dict(min_interval or {})
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self._sleep = sleep
        self._last_call: dict[str, float] = {}
        self._pace_lock = threading.Lock()

    def get(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        as_json: bool = True,
        slim: Optional[Callable[[Any], Any]] = None,
    ) -> Response:
        """GET ``url`` and return a :class:`Response`.

        ``slim`` trims a successful payload before it is cached and returned, which
        keeps recorded fixtures small. Non-2xx statuses are returned, not raised;
        only transport-level failures raise :class:`HttpError`.
        """
        key = cache_key(url, params)
        hit = self.cache.get(key)
        if hit is not None:
            return Response(status=int(hit["status"]), data=hit.get("data"))
        if self.offline:
            raise OfflineCacheMiss(f"not in offline cache: {key}")

        resp = self._fetch(url, params)
        data: Any = None
        if resp.status_code == 200:
            try:
                data = resp.json() if as_json else resp.text
            except ValueError as exc:
                raise HttpError(f"invalid JSON from {urlsplit(url).netloc}") from exc
            if slim is not None:
                data = slim(data)
        out = Response(status=resp.status_code, data=data)
        if is_cacheable(resp.status_code):
            self.cache.set(key, {"status": out.status, "data": out.data})
        return out

    # ── internals ────────────────────────────────────────────────────────────

    def _pace(self, host: str) -> None:
        interval = self.min_interval.get(host, 0.0)
        if interval <= 0:
            return
        with self._pace_lock:
            wait = self._last_call.get(host, 0.0) + interval - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            self._last_call[host] = time.monotonic()

    def _fetch(self, url: str, params: Optional[Mapping[str, Any]]) -> requests.Response:
        host = urlsplit(url).netloc
        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            self._pace(host)
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
            else:
                if resp.status_code not in RETRY_STATUS or attempt == self.retries:
                    return resp
                last_error = HttpError(f"HTTP {resp.status_code} from {host}")
                retry_after = resp.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    self._sleep(min(float(retry_after), 10.0))
                    continue
            if attempt < self.retries:
                self._sleep(self.backoff * (2 ** attempt))
        raise HttpError(f"request to {host} failed: {last_error}") from last_error
