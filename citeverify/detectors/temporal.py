"""Tier: reject citations dated in the future."""
from __future__ import annotations

from datetime import date
from typing import Optional

from citeverify.detectors import ACTION_REMOVE, HALLUCINATED, Decision
from citeverify.models import ParsedCitation, Signal

#: Papers dated next year are common (online-first, "in press"), so allow one year of slack.
FUTURE_SLACK_YEARS = 1


def check(parsed: ParsedCitation, current_year: Optional[int] = None) -> tuple[Optional[Decision], Signal]:
    """Return a HALLUCINATED decision if the cited year is impossible, plus the signal."""
    year_now = current_year or date.today().year
    if parsed.year is None:
        return None, Signal("Publication year", "skip", "No year found in the citation text.")
    if parsed.year > year_now + FUTURE_SLACK_YEARS:
        sig = Signal("Publication year", "fail", f"{parsed.year} is in the future (current year {year_now}).")
        return Decision(
            score=0.02, verdict=HALLUCINATED, sub="Future publication date",
            explanation=f"The citation is dated {parsed.year}, which has not happened yet.",
            action=ACTION_REMOVE, signals=[sig],
        ), sig
    return None, Signal("Publication year", "pass", f"{parsed.year} is a plausible publication year.")
