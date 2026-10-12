"""HTTP API for CiteVerify.

    uvicorn citeverify.api:app --port 8000        # interactive docs at /docs

Endpoints
    GET  /health            liveness, version, whether the risk model is loaded
    POST /v1/audit          one citation
    POST /v1/audit/batch    up to 100 citations, checked concurrently, order kept

Registry responses are cached in memory for the life of the process, so repeated
requests for the same DOI or title make no new network calls.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from citeverify import __version__
from citeverify.models import AuditResult
from citeverify.pipeline import default_auditor
from citeverify.risk import load_model

MAX_TEXT = 2000
MAX_BATCH = 100

app = FastAPI(
    title="CiteVerify API",
    version=__version__,
    description="Checks whether academic references are real and correctly cited, against Crossref, "
                "DataCite and arXiv, and returns the evidence plus a calibrated risk of fabrication.",
)


class CitationIn(BaseModel):
    citation: str = Field(..., min_length=1, max_length=MAX_TEXT,
                          examples=["He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning "
                                    "for image recognition. CVPR."])
    doi: Optional[str] = Field(None, max_length=200, description="DOI or arXiv ID, if known",
                               examples=["10.1109/CVPR.2016.90"])


class BatchIn(BaseModel):
    items: list[CitationIn] = Field(..., min_length=1, max_length=MAX_BATCH)


class Evidence(BaseModel):
    check: str
    status: str
    detail: str


class MatchedRecord(BaseModel):
    source: str
    title: str
    year: Optional[int]
    authors: list[str]
    doi: Optional[str]


class AuditOut(BaseModel):
    label: str = Field(description="VERIFIED, UNCERTAIN or HALLUCINATED (rule-based verdict)")
    score: float = Field(description="Rule score: 0 = fabricated, 1 = genuine")
    risk: Optional[float] = Field(description="Calibrated probability that the citation is fabricated")
    risk_flagged: Optional[bool] = Field(description="risk is at or above the model's flag threshold")
    reason: str
    explanation: str
    action: str
    decided_by: str
    evidence: list[Evidence]
    record: Optional[MatchedRecord]
    error: Optional[str] = Field(description="Set when a registry could not be reached")


class Health(BaseModel):
    status: str
    version: str
    risk_model: bool


def to_out(r: AuditResult) -> AuditOut:
    model = load_model()
    rec = r.record
    return AuditOut(
        label=r.label, score=round(r.score, 4),
        risk=round(r.risk, 4) if r.risk is not None else None,
        risk_flagged=model.flagged(r.risk) if (model and r.risk is not None) else None,
        reason=r.sub, explanation=r.explanation, action=r.action, decided_by=r.tier,
        evidence=[Evidence(check=s.name, status=s.status, detail=s.detail) for s in r.signals],
        record=MatchedRecord(source=rec.source, title=rec.title, year=rec.year, authors=list(rec.authors),
                             doi=rec.doi) if rec else None,
        error=r.error,
    )


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", version=__version__, risk_model=load_model() is not None)


@app.post("/v1/audit", response_model=AuditOut)
def audit(item: CitationIn) -> AuditOut:
    return to_out(default_auditor().audit(item.citation, item.doi))


@app.post("/v1/audit/batch", response_model=list[AuditOut])
def audit_batch(batch: BatchIn) -> list[AuditOut]:
    results = default_auditor().audit_many([(i.citation, i.doi) for i in batch.items], max_workers=4)
    return [to_out(r) for r in results]
