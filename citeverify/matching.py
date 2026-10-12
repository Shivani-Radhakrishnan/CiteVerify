"""Compare what a citation claims against what a registry record says."""
from __future__ import annotations

import re
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

    The score is the best of: a character-level ratio of the folded strings, that ratio
    averaged with the content-word Dice coefficient, and (when both have at least three
    words) a main-title comparison that ignores everything after the first colon.
    """
    a, b = fold(claimed), fold(actual)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    seq = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(content_tokens(claimed)), set(content_tokens(actual))
    dice = 2 * len(ta & tb) / (len(ta) + len(tb)) if ta and tb else 0.0
    # Word overlap alone ignores order ("graph networks for classification" vs
    # "classification with graph networks"), so it only counts blended with the
    # order-sensitive ratio.
    best = max(seq, (seq + dice) / 2)
    main_a, main_b = fold(claimed.split(":")[0]), fold(actual.split(":")[0])
    if main_a and main_b and min(len(main_a.split()), len(main_b.split())) >= 3:
        best = max(best, SequenceMatcher(None, main_a, main_b).ratio() * 0.95)
    return round(best, 4)


def title_in_text(title: str, text: str) -> float:
    """0.95 if a registry title appears verbatim in the citation text, 0.9 for its main
    title (before a colon), else 0. Spaces are ignored, so "retrievalaugmented" matches
    "Retrieval-Augmented". Titles under three content words or 20 letters never count.
    """
    haystack = fold(text).replace(" ", "")
    for part, score in ((title, 0.95), (title.split(":")[0], 0.90)):
        needle = fold(part).replace(" ", "")
        if len(content_tokens(part)) >= 3 and len(needle) >= 20 and needle in haystack:
            return score
    return 0.0


#: Registry records that are about another work rather than the work itself.
_DERIVATIVE = re.compile(
    r"^(?:erratum|corrigendum|correction|author correction|publisher correction|"
    r"retraction note|review of|comment on|reply to|response to|addendum)\b"
)


def is_derivative(title: str) -> bool:
    """True for errata, corrections, reviews, comments and replies."""
    return bool(_DERIVATIVE.match(fold(title)))


_GROUP_AUTHOR = re.compile(
    r"\b(?:consortium|collaboration|group|team|project|initiative|committee|network|"
    r"society|association|organi[sz]ation|institute|council|investigators)\b"
)


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
    is_preprint = record.source == "arXiv" or (record.doi or "").lower().startswith("10.48550/")
    if is_preprint and 0 < parsed.year - years[0] <= 3:
        # A paper posted to arXiv is normally cited by the year it appeared at a venue
        # (Kipf & Welling: arXiv 2016, ICLR 2017), so a later year is the expected case.
        return FieldCheck(
            "Year", "match",
            f"Cited {parsed.year}; arXiv preprint from {years[0]} (published versions come later).",
        )
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
    if _GROUP_AUTHOR.search(fold(record.authors[0])):
        return FieldCheck("First author", "unchecked", f"Registry lists a group author ({record.authors[0]}).")
    key = _surname_key(claimed)
    keys = [_surname_key(a) for a in record.authors]
    if key == keys[0] or fold(claimed) == fold(record.authors[0]):
        return FieldCheck("First author", "match", f"{claimed} is the first author.")
    if keys[0] and keys[0] in fold(parsed.cleaned).split()[:12]:
        # the parser may have mis-split the author list; the real first author is named up front
        return FieldCheck("First author", "match", f"{record.authors[0]} (first author) is named in the citation.")
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


def candidate_similarity(parsed: ParsedCitation, record: WorkRecord) -> float:
    """How well ``record`` matches the citation: parsed-title similarity, or the record's
    title appearing verbatim in the citation (robust to a mis-parsed title)."""
    sim = title_similarity(parsed.title, record.title)
    # A record whose title is the citation's venue (a proceedings volume, a journal)
    # is contained in the text without being the cited work.
    if parsed.venue and title_similarity(parsed.venue, record.title) >= TITLE_MATCH:
        return sim
    return max(sim, title_in_text(record.title, parsed.cleaned))


@dataclass(frozen=True)
class Match:
    record: Optional[WorkRecord]
    similarity: float
    checks: tuple[FieldCheck, ...] = ()

    @property
    def consistent(self) -> bool:
        """Title matches and neither year nor first author contradicts the citation."""
        return self.similarity >= TITLE_MATCH and all(c.status != "mismatch" for c in self.checks)


def best_match(parsed: ParsedCitation, candidates: list[WorkRecord]) -> Match:
    """Pick the registry record that best explains the citation.

    Errata, reviews and similar derivative records are ignored. Among records whose
    title matches, one whose year and first author also agree is preferred, so a
    preprint/erratum sharing the title does not make a correct citation look wrong.
    """
    want_derivative = is_derivative(parsed.title)
    scored = [(candidate_similarity(parsed, c), c) for c in candidates
              if want_derivative or not is_derivative(c.title)]
    if not scored:
        return Match(None, 0.0)
    matching = [(sim, c) for sim, c in scored if sim >= TITLE_MATCH]
    if not matching:
        sim, rec = max(scored, key=lambda sc: sc[0])
        return Match(rec, sim)
    ranked = []
    for sim, c in matching:
        checks = (check_year(parsed, c), check_first_author(parsed, c))
        bad = sum(ch.status == "mismatch" for ch in checks)
        minor = sum(ch.status == "minor" for ch in checks)
        ranked.append(((bad, minor, -sim), Match(c, sim, checks)))
    return min(ranked, key=lambda r: r[0])[1]
