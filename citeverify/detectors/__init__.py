"""Detection tiers. Each tier either returns a :class:`Decision` or passes (``None``)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from citeverify.models import Signal, WorkRecord


@dataclass
class Decision:
    """A tier's verdict. ``score`` follows :class:`~citeverify.models.AuditResult`."""

    score: float
    verdict: str
    sub: str
    explanation: str
    action: str
    signals: list[Signal] = field(default_factory=list)
    record: Optional[WorkRecord] = None
    error: Optional[str] = None
    features: dict[str, Any] = field(default_factory=dict)


# Verdict wording shared by the tiers.
VERIFIED = "Verified real"
LIKELY_REAL = "Likely real"
NEEDS_REVIEW = "Needs review"
HALLUCINATED = "Likely hallucinated"

ACTION_NONE = "No action needed."
ACTION_REVIEW = "Check this reference by hand before relying on it."
ACTION_REMOVE = "Remove or replace this citation."
