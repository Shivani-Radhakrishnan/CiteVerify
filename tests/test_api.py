"""REST API: request validation, response shape, batch order. Registries are mocked."""
import pytest
from fastapi.testclient import TestClient

import citeverify.api as api
from tests.test_pipeline import HE, HE_DOI, he_record


@pytest.fixture
def client(make_auditor, registry, monkeypatch):
    auditor = make_auditor()
    monkeypatch.setattr(api, "default_auditor", lambda: auditor)
    return TestClient(api.app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["risk_model"] is True


def test_audit_verified_with_evidence_and_risk(client, registry):
    he_record(registry)
    body = client.post("/v1/audit", json={"citation": HE, "doi": HE_DOI}).json()
    assert body["label"] == "VERIFIED" and body["decided_by"] == "DOI registry"
    assert body["record"]["doi"].lower() == HE_DOI.lower() and body["record"]["year"] == 2016
    assert 0 <= body["risk"] < 0.05 and body["risk_flagged"] is False
    assert {e["check"] for e in body["evidence"]} >= {"DOI lookup", "Title", "Year", "First author"}


def test_future_year_needs_no_registry(client):
    body = client.post("/v1/audit", json={"citation": HE.replace("2016", "2031")}).json()
    assert body["label"] == "HALLUCINATED" and body["decided_by"] == "Temporal check"


def test_batch_keeps_order(client, registry):
    he_record(registry)
    items = [{"citation": HE.replace("2016", "2031")}, {"citation": HE, "doi": HE_DOI}]
    labels = [r["label"] for r in client.post("/v1/audit/batch", json={"items": items}).json()]
    assert labels == ["HALLUCINATED", "VERIFIED"]


@pytest.mark.parametrize("payload", [
    {"citation": ""},
    {"citation": "x" * (api.MAX_TEXT + 1)},
    {"doi": "10.1/x"},
])
def test_invalid_single_requests_are_rejected(client, payload):
    assert client.post("/v1/audit", json=payload).status_code == 422


def test_batch_limits(client):
    assert client.post("/v1/audit/batch", json={"items": []}).status_code == 422
    too_many = [{"citation": "a"}] * (api.MAX_BATCH + 1)
    assert client.post("/v1/audit/batch", json={"items": too_many}).status_code == 422
