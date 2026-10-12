"""Data types shared across the package."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Label(str, Enum):
    """Three-way outcome shown to the user."""

    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    HALLUCINATED = "HALLUCINATED"


class Tier(str, Enum):
    """Pipeline stage that produced the final verdict."""

    TEMPORAL = "Temporal check"
    DOI = "DOI registry"
    KNOWN = "Known-papers table (legacy)"
    SEARCH = "Registry search"
    HEURISTIC = "Plausibility heuristics"


@dataclass(frozen=True)
class WorkRecord:
    """Bibliographic metadata for one work, as returned by a registry."""

    source: str  # "Crossref" | "DataCite" | "arXiv"
    title: str
    authors: tuple[str, ...] = ()  # family names, in order
    years: frozenset[int] = frozenset()  # every publication year the registry lists
    doi: Optional[str] = None
    venue: str = ""
    url: str = ""

    @property
    def year(self) -> Optional[int]:
        return min(self.years) if self.years else None


@dataclass(frozen=True)
class ParsedCitation:
    """Fields extracted from free-text citation."""

    raw: str
    cleaned: str
    authors: tuple[str, ...] = ()  # family names, in order
    year: Optional[int] = None
    title: str = ""
    venue: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    style: str = "freeform"  # "apa" | "ieee" | "vancouver" | "lowercase" | "freeform"

    @property
    def first_author(self) -> Optional[str]:
        return self.authors[0] if self.authors else None


@dataclass(frozen=True)
class Signal:
    """One piece of evidence. ``status`` is ``pass``, ``fail``, ``warn``, ``info`` or ``skip``."""

    name: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class Stage:
    """Whether a pipeline stage ``decided`` the verdict, ``passed`` it on, or was ``skipped``."""

    tier: Tier
    status: str
    note: str = ""


@dataclass
class AuditResult:
    """The outcome of auditing one citation.

    ``score`` is a 0-1 plausibility that the citation is genuine and correct; the
    three-way :attr:`label` is derived from it with ``threshold`` (scores below the
    threshold are HALLUCINATED, scores of at least 0.70 are VERIFIED).
    """

    verdict: str
    sub: str
    tier: str
    explanation: str
    action: str
    score: float
    threshold: float = 0.20
    signals: list[Signal] = field(default_factory=list)
    trace: list[Stage] = field(default_factory=list)
    parsed: Optional[ParsedCitation] = None
    record: Optional[WorkRecord] = None
    features: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None  # set when a registry could not be reached

    VERIFIED_AT = 0.70

    @property
    def label(self) -> str:
        if self.score < self.threshold:
            return Label.HALLUCINATED.value
        if self.score >= self.VERIFIED_AT:
            return Label.VERIFIED.value
        return Label.UNCERTAIN.value

    @property
    def is_flagged(self) -> bool:
        """Binary prediction used for evaluation: flagged as hallucinated."""
        return self.label == Label.HALLUCINATED.value

    @property
    def confidence(self) -> float:
        """Confidence in the label's direction (score for real, 1 - score for fake)."""
        return self.score if self.score >= 0.5 else 1.0 - self.score

    @property
    def confidence_pct(self) -> str:
        return f"{self.confidence * 100:.0f}%"

    def to_row(self) -> dict[str, Any]:
        """Flat dict for tables and CSV export."""
        return {
            "label": self.label,
            "score": round(self.score, 3),
            "verdict": self.verdict,
            "reason": self.sub,
            "tier": self.tier,
            "explanation": self.explanation,
            "action": self.action,
            "matched_doi": self.record.doi if self.record else "",
            "error": self.error or "",
        }
