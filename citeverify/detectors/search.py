"""Tier: when no DOI is given, look the citation up by title in Crossref and arXiv."""
from __future__ import annotations

from typing import Optional

from citeverify.clients.registries import ArxivClient, CrossrefClient
from citeverify.detectors import (
    ACTION_NONE, ACTION_REMOVE, ACTION_REVIEW, HALLUCINATED, LIKELY_REAL, NEEDS_REVIEW, VERIFIED,
    Decision,
)
from citeverify.matching import TITLE_MATCH, TITLE_MISMATCH, content_tokens, best_match, check_first_author, check_year
from citeverify.models import ParsedCitation, Signal

#: Titles with fewer content words are too generic to search for reliably.
MIN_TITLE_TOKENS = 3
#: A title this specific that matches a record credited to other people is treated as
#: misattributed rather than as a coincidental title collision.
SPECIFIC_TITLE_TOKENS = 4


class RegistrySearch:
    """Find the citation's title in Crossref (bibliographic query) and, failing that, arXiv.

    ``not_found_score`` is the score given when neither registry has a record with a
    similar title. Absence is evidence of fabrication but not proof (books, reports and
    theses are often unindexed), so it is a tunable parameter, chosen on the dev split.
    """

    def __init__(self, crossref: CrossrefClient, arxiv: ArxivClient, not_found_score: float = 0.15) -> None:
        self.crossref, self.arxiv = crossref, arxiv
        self.not_found_score = not_found_score

    @staticmethod
    def applicable(parsed: ParsedCitation) -> bool:
        return len(content_tokens(parsed.title)) >= MIN_TITLE_TOKENS

    def check(self, parsed: ParsedCitation) -> Optional[Decision]:
        """Return a decision, or ``None`` if the citation has no usable title.

        Raises :class:`~citeverify.clients.http.HttpError` if a registry is unreachable.
        """
        if not self.applicable(parsed):
            return None
        candidates = self.crossref.search(parsed.cleaned)
        best, sim = best_match(parsed, candidates)
        sources = "Crossref"
        if sim < TITLE_MATCH:
            arxiv_best, arxiv_sim = best_match(parsed, self.arxiv.search_title(parsed.title))
            sources = "Crossref and arXiv"
            if arxiv_sim > sim:
                best, sim = arxiv_best, arxiv_sim

        if best is None or sim < TITLE_MISMATCH:
            closest = f' Closest title: "{best.title[:80]}" ({sim:.2f}).' if best else ""
            return Decision(
                score=self.not_found_score, verdict=HALLUCINATED if self.not_found_score < 0.2 else NEEDS_REVIEW,
                sub="No matching record found",
                explanation=f"No work with this title was found in {sources}.{closest}",
                action=ACTION_REMOVE if self.not_found_score < 0.2 else ACTION_REVIEW,
                signals=[Signal("Registry search", "fail", f"No similar title in {sources}.")],
            )
        title_sig = Signal("Title", "pass" if sim >= TITLE_MATCH else "warn",
                           f'Closest record: "{best.title[:90]}" in {best.source} (similarity {sim:.2f}).')
        if sim < TITLE_MATCH:
            return Decision(
                score=0.4, verdict=NEEDS_REVIEW, sub="Only a partial title match",
                explanation=title_sig.detail, action=ACTION_REVIEW,
                signals=[Signal("Registry search", "warn", "Only a partial match."), title_sig], record=best,
            )

        checks = [check_year(parsed, best), check_first_author(parsed, best)]
        signals = [Signal("Registry search", "pass", f"Found in {best.source}."), title_sig] + [
            c.to_signal() for c in checks
        ]
        bad = [c for c in checks if c.status == "mismatch"]
        if bad:
            specific = len(content_tokens(parsed.title)) >= SPECIFIC_TITLE_TOKENS
            return Decision(
                score=0.1 if specific else 0.35,
                verdict=HALLUCINATED if specific else NEEDS_REVIEW,
                sub="Title exists but is credited differently",
                explanation=" ".join(c.detail for c in bad),
                action=ACTION_REMOVE if specific else ACTION_REVIEW,
                signals=signals, record=best,
            )
        if any(c.status == "minor" for c in checks):
            return Decision(
                score=0.55, verdict=LIKELY_REAL, sub="Found, with a small discrepancy",
                explanation=" ".join(c.detail for c in checks if c.status == "minor"),
                action=ACTION_REVIEW, signals=signals, record=best,
            )
        where = f" (DOI {best.doi})" if best.doi else ""
        return Decision(
            score=0.9, verdict=VERIFIED, sub=f"Found in {best.source}",
            explanation=f"A {best.source} record{where} matches the title"
                        + (", year and first author." if all(c.status == "match" for c in checks) else "."),
            action=ACTION_NONE, signals=signals, record=best,
        )
