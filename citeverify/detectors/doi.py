"""Tier: verify a DOI against the registries and compare the cited metadata."""
from __future__ import annotations

from typing import Optional

from citeverify.clients.http import HttpError
from citeverify.clients.registries import ArxivClient, CrossrefClient, DataCiteClient, DoiOrgClient
from citeverify.detectors import (
    ACTION_NONE, ACTION_REMOVE, ACTION_REVIEW, HALLUCINATED, LIKELY_REAL, NEEDS_REVIEW, VERIFIED,
    Decision,
)
from citeverify.matching import FieldCheck, compare
from citeverify.models import ParsedCitation, Signal, WorkRecord
from citeverify.parsing import arxiv_id_from_doi


class DoiVerifier:
    """Resolve a DOI and check that the citation's title, year and first author match it.

    Routing: arXiv DOIs (``10.48550/arXiv.*``) go to DataCite, then the arXiv API. All
    other DOIs go to Crossref, then DataCite. If neither has metadata, the doi.org
    handle API decides whether the DOI exists at all (another agency may hold it).
    """

    def __init__(self, crossref: CrossrefClient, datacite: DataCiteClient,
                 arxiv: ArxivClient, doi_org: DoiOrgClient) -> None:
        self.crossref, self.datacite, self.arxiv, self.doi_org = crossref, datacite, arxiv, doi_org

    def _resolve(self, doi: str) -> tuple[Optional[WorkRecord], bool]:
        """(record, exists). ``record`` is None when no registry returned metadata."""
        arxiv_id = arxiv_id_from_doi(doi)
        if arxiv_id:
            rec = self.datacite.get_work(doi) or self.arxiv.get_work(arxiv_id)
            return rec, rec is not None
        rec = self.crossref.get_work(doi) or self.datacite.get_work(doi)
        if rec is not None:
            return rec, True
        return None, self.doi_org.exists(doi)

    def check(self, parsed: ParsedCitation, doi: str) -> Decision:
        try:
            record, exists = self._resolve(doi)
        except HttpError as exc:
            return Decision(
                score=0.5, verdict=NEEDS_REVIEW, sub="Registry unreachable",
                explanation=f"Could not reach the DOI registries ({exc}). Nothing was concluded.",
                action=f"Retry later or open https://doi.org/{doi} by hand.",
                signals=[Signal("DOI lookup", "warn", str(exc))], error=str(exc),
            )
        if record is None and not exists:
            return Decision(
                score=0.02, verdict=HALLUCINATED, sub="DOI does not exist",
                explanation=f"{doi} is not registered with Crossref, DataCite, arXiv or doi.org.",
                action=ACTION_REMOVE,
                signals=[Signal("DOI lookup", "fail", f"{doi} does not resolve.")],
            )
        if record is None:
            return Decision(
                score=0.5, verdict=NEEDS_REVIEW, sub="DOI registered elsewhere",
                explanation=(f"{doi} exists, but its registration agency does not expose metadata "
                             "to compare against."),
                action=f"Open https://doi.org/{doi} and compare the details by hand.",
                signals=[Signal("DOI lookup", "pass", "DOI exists (doi.org)."),
                         Signal("Metadata", "skip", "No Crossref/DataCite/arXiv record.")],
            )
        checks = compare(parsed, record)
        return decide_from_checks(checks, record, doi)


def decide_from_checks(checks: list[FieldCheck], record: WorkRecord, doi: str) -> Decision:
    signals = [Signal("DOI lookup", "pass", f"Found in {record.source}.")] + [c.to_signal() for c in checks]
    status = {c.field: c.status for c in checks}
    bad = [c for c in checks if c.status == "mismatch"]
    minor = [c for c in checks if c.status == "minor"]
    if bad:
        return Decision(
            score=0.05, verdict=HALLUCINATED, sub="DOI exists but details do not match",
            explanation=" ".join(c.detail for c in bad),
            action="The DOI is real but points to a different work, or the cited details are wrong. "
                   + ACTION_REMOVE,
            signals=signals, record=record,
        )
    if minor:
        return Decision(
            score=0.5, verdict=LIKELY_REAL, sub="Small discrepancy with the registry",
            explanation=" ".join(c.detail for c in minor), action=ACTION_REVIEW,
            signals=signals, record=record,
        )
    if status["Title"] == "unchecked" and status["First author"] == "unchecked":
        return Decision(
            score=0.6, verdict=LIKELY_REAL, sub="DOI exists; too little text to compare",
            explanation=f"{doi} is registered in {record.source}, but the citation has no title or "
                        "author to compare against it.",
            action=ACTION_REVIEW, signals=signals, record=record,
        )
    return Decision(
        score=0.97, verdict=VERIFIED, sub=f"Confirmed by {record.source}",
        explanation=" ".join(c.detail for c in checks if c.status == "match"),
        action=ACTION_NONE, signals=signals, record=record,
    )
