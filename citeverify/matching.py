"""Compare what a citation claims against what a registry record says."""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from citeverify.models import ParsedCitation, Signal, WorkRecord
from citeverify.parsing import fold

#: Title similarity at or above this is treated as the same title.
TITLE_MATCH = 0.85
#: Below this the titles are treated as different works.
TITLE_MISMATCH = 0.60

_STOP = {
    "a", "an", "the", "of", "for", "and", "in", "on", "to", "with", "by", "from", "via",
    "using", "at", "as", "is", "its", "towards", "toward",
}


def content_tokens(text: str) -> list[str]:
    return [t for t in fold(text).split() if t not in _STOP]


def title_similarity(claimed: str, actual: str) -> float:
    """0-1 similarity between two titles, robust to case, accents, punctuation and subtitles.

    The score is the best of: a character-level ratio of the folded strings, the token
    Dice coefficient, and (when both have at least three content words) a main-title
    comparison that ignores everything after the first colon.
    """
    a, b = fold(claimed), fold(actual)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(content_tokens(claimed)), set(content_tokens(actual))
    dice = 2 * len(ta & tb) / (len(ta) + len(tb)) if ta and tb else 0.0
    best = max(seq, dice)
    main_a, main_b = fold(claimed.split(":")[0]), fold(actual.split(":")[0])
    if main_a and main_b and min(len(main_a.split()), len(main_b.split())) >= 3:
        best = max(best, SequenceMatcher(None, main_a, main_b).ratio() * 0.95)
    return round(best, 4)


def _surname_key(name: str) -> str:
    """Last folded token of a surname: 'van der Walt' -> 'walt', 'Barabási' -> 'barabasi'."""
    parts = fold(name).split()
    return parts[-1] if parts else ""


@dataclass(frozen=True)
class FieldCheck:
    """Result of checking one field. ``status``: match | minor | mismatch | unchecked."""

    field: str
    status: str
    detail: str

    def to_signal(self) -> Signal:
        status = {"match": "pass", "minor": "warn", "mismatch": "fail"}.get(self.status, "skip")
        return Signal(self.field, status, self.detail)


def check_title(parsed: ParsedCitation, record: WorkRecord) -> FieldCheck:
    if not parsed.title or len(content_tokens(parsed.title)) < 2:
        return FieldCheck("Title", "unchecked", "No title found in the citation text.")
    if not record.title:
        return FieldCheck("Title", "unchecked", f"{record.source} record has no title.")
    sim = title_similarity(parsed.title, record.title)
    shown = record.title if len(record.title) <= 90 else record.title[:87] + "..."
    if sim >= TITLE_MATCH:
        return FieldCheck("Title", "match", f"Matches the registry title (similarity {sim:.2f}).")
    if sim >= TITLE_MISMATCH:
        return FieldCheck("Title", "minor", f'Partly matches "{shown}" (similarity {sim:.2f}).')
    return FieldCheck("Title", "mismatch", f'Registry title is "{shown}" (similarity {sim:.2f}).')


def check_year(parsed: ParsedCitation, record: WorkRecord) -> FieldCheck:
    if parsed.year is None:
        return FieldCheck("Year", "unchecked", "No year found in the citation text.")
    if not record.years:
        return FieldCheck("Year", "unchecked", f"{record.source} record has no date.")
    years = sorted(record.years)
    listed = "/".join(map(str, years))
    if parsed.year in record.years:
        return FieldCheck("Year", "match", f"{parsed.year} matches the registry ({listed}).")
    gap = min(abs(parsed.year - y) for y in years)
    if gap == 1:
        return FieldCheck(
            "Year", "minor",
            f"Cited {parsed.year}; registry lists {listed} (off by one: often online-first or preprint vs. print).",
        )
    return FieldCheck("Year", "mismatch", f"Cited {parsed.year}; registry lists {listed}.")


def check_first_author(parsed: ParsedCitation, record: WorkRecord) -> FieldCheck:
    claimed = parsed.first_author
    if not claimed:
        return FieldCheck("First author", "unchecked", "No author found in the citation text.")
    if not record.authors:
        return FieldCheck("First author", "unchecked", f"{record.source} record lists no personal authors.")
    key = _surname_key(claimed)
    keys = [_surname_key(a) for a in record.authors]
    if key == keys[0] or fold(claimed) == fold(record.authors[0]):
        return FieldCheck("First author", "match", f"{claimed} is the first author.")
    if key in keys:
        return FieldCheck(
            "First author", "minor",
            f"{claimed} is an author, but the registry lists {record.authors[0]} first.",
        )
    return FieldCheck(
        "First author", "mismatch",
        f"Cited {claimed}; registry lists {', '.join(record.authors[:3])}"
        + (" et al." if len(record.authors) > 3 else "") + ".",
    )


def compare(parsed: ParsedCitation, record: WorkRecord) -> list[FieldCheck]:
    """Title, year and first-author checks for ``parsed`` against ``record``."""
    return [check_title(parsed, record), check_year(parsed, record), check_first_author(parsed, record)]


def best_match(parsed: ParsedCitation, candidates: list[WorkRecord]) -> tuple[Optional[WorkRecord], float]:
    """The candidate whose title is most similar to the citation's title."""
    best, best_sim = None, 0.0
    for c in candidates:
        sim = title_similarity(parsed.title, c.title)
        if sim > best_sim:
            best, best_sim = c, sim
    return best, best_sim
