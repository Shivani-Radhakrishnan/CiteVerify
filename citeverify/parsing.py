"""Turn free-text citations into structured fields (authors, year, title, venue, DOI).

The parser understands the common reference styles (APA, IEEE, Vancouver), the
lower-case "surname initial year title" form used by the original study data, and
inline mentions ("as shown by Smith et al. 2020"). It is deliberately conservative:
a field it cannot find is left empty rather than guessed, and downstream checks treat
empty fields as "not checked".
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional
from urllib.parse import unquote

from citeverify.models import ParsedCitation

# ── identifiers ───────────────────────────────────────────────────────────────

_DOI_BODY = r"10\.\d{4,9}/[^\s\"<>]+"
_DOI_IN_TEXT = re.compile(rf"(?:doi\s*[:：]?\s*|https?://(?:dx\.)?doi\.org/)?({_DOI_BODY})", re.I)
_DOI_PREFIX = re.compile(r"^(?:https?://)?(?:dx\.|www\.)?doi\.org/|^doi\s*[:：]?\s*", re.I)
_ARXIV_NEW = r"\d{4}\.\d{4,5}"
_ARXIV_OLD = r"[a-z\-]+(?:\.[A-Z]{2})?/\d{7}"
_ARXIV_IN_TEXT = re.compile(
    rf"arxiv(?:\.org/abs/|\s*[:：]\s*|\s+)({_ARXIV_NEW}|{_ARXIV_OLD})(v\d+)?", re.I
)


def normalise_doi(raw: object) -> Optional[str]:
    """Return the bare DOI (``10.xxxx/...``) or ``None`` if ``raw`` is not a DOI.

    Accepts ``doi:`` prefixes, ``https://doi.org/`` and ``dx.doi.org`` URLs, URL-encoding
    and trailing punctuation picked up from running text.
    """
    if raw is None:
        return None
    s = unquote(str(raw)).strip()
    s = _DOI_PREFIX.sub("", s).strip()
    s = s.rstrip(".,;:'\"]>")
    while s.endswith(")") and s.count(")") > s.count("("):
        s = s[:-1]
    return s if re.fullmatch(_DOI_BODY, s) else None


def find_doi(text: str) -> Optional[str]:
    """First DOI mentioned anywhere in ``text``."""
    m = _DOI_IN_TEXT.search(text or "")
    return normalise_doi(m.group(1)) if m else None


def arxiv_id_from_doi(doi: str) -> Optional[str]:
    """``10.48550/arXiv.1706.03762`` -> ``1706.03762`` (version suffix removed)."""
    m = re.fullmatch(rf"10\.48550/arxiv\.({_ARXIV_NEW}|{_ARXIV_OLD})(v\d+)?", doi or "", re.I)
    return m.group(1) if m else None


def find_arxiv_id(text: str) -> Optional[str]:
    """arXiv identifier written as ``arXiv:1706.03762`` / ``arxiv.org/abs/...`` in text."""
    m = _ARXIV_IN_TEXT.search(text or "")
    return m.group(1) if m else None


# ── text helpers ──────────────────────────────────────────────────────────────

def fold(text: str) -> str:
    """Lower-case, strip accents and collapse everything except letters/digits to spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^0-9a-z]+", " ", text.lower())
    return text.strip()


_LEADING_CONTEXT = [
    r"^as\s+(?:suggested|shown|demonstrated|proposed|discussed|reported|noted)\s+(?:by|in)\s+",
    r"^according\s+to\s+",
    r"^following\s+",
    r"^based\s+on\s+",
    r"^see\s+(?:also\s+)?",
    r"^cf\.?\s+",
]
_TRAILING_CONTEXT = [r",\s+which\s+.*$", r",\s+demonstrating\s+.*$", r",\s+showing\s+.*$"]


def extract_core_citation(text: str) -> str:
    """Strip inline-prose wrappers ("as shown by ...", ", which ...") and list markers."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    t = re.sub(r"^\s*(?:\[\d+\]|\d+\.(?=\s)|[-•*])\s*", "", t)
    for p in _LEADING_CONTEXT:
        t = re.sub(p, "", t, flags=re.I)
    for p in _TRAILING_CONTEXT:
        t = re.sub(p, "", t, flags=re.I)
    return t.strip()


# ── years ─────────────────────────────────────────────────────────────────────

_YEAR = r"(1[5-9]\d\d|20\d\d)"


def _strip_identifiers(text: str) -> str:
    text = _DOI_IN_TEXT.sub(" ", text)
    text = _ARXIV_IN_TEXT.sub(" ", text)
    return re.sub(r"https?://\S+", " ", text)


def extract_year(text: str) -> Optional[int]:
    """Publication year, preferring ``(2016)``, then a year closing the citation.

    Page ranges (``1735-1780``) and numbers inside DOIs/URLs are ignored.
    """
    t = _strip_identifiers(text or "")
    t = re.sub(r"\d+\s*[-–—]\s*\d+", " ", t)  # page ranges
    m = re.search(rf"\(\s*{_YEAR}[a-z]?\s*[,)]", t)
    if m:
        return int(m.group(1))
    m = re.search(rf"(?<![\d.]){_YEAR}[a-z]?\W*$", t)
    if m:
        return int(m.group(1))
    m = re.search(rf"(?<![\d./]){_YEAR}[a-z]?(?![\d])", t)
    return int(m.group(1)) if m else None


# ── authors ───────────────────────────────────────────────────────────────────

_INITIALS_TOKEN = re.compile(r"^(?:[A-Z]\.?(?:-?[A-Z]\.?)*|[A-Z]{1,3})$")
_PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "da", "di", "le", "la", "du", "dos", "ter"}


def _surname_from_piece(piece: str) -> Optional[str]:
    tokens = [t for t in re.split(r"\s+", piece.strip().strip(".,")) if t]
    keep = [t for t in tokens if not _INITIALS_TOKEN.match(t.strip(".,"))]
    keep = [t.strip(".,") for t in keep if t.lower().strip(".") not in {"et", "al", "and", "&"}]
    if not keep:
        return None
    if not any(c.isalpha() for c in "".join(keep)):
        return None
    return " ".join(keep)


def parse_authors(segment: str) -> tuple[str, ...]:
    """Family names from an author list in APA, IEEE, Vancouver or lower-case form."""
    seg = re.sub(r"\bet\s+al\b\.?", "", segment or "", flags=re.I)
    if seg.islower() and "," not in seg:  # "vaswani a shazeer n"
        return _lowercase_authors(seg.split())[0]
    seg = re.sub(r"\s*(?:&|\band\b)\s*", ", ", seg)
    pieces = [p.strip() for p in seg.split(",") if p.strip()]
    names: list[str] = []
    for piece in pieces:
        if _INITIALS_TOKEN.match(piece.replace(" ", "").strip(".")) or all(
            _INITIALS_TOKEN.match(t) for t in piece.split()
        ):
            continue  # APA "K." piece that belongs to the previous surname
        name = _surname_from_piece(piece)
        if name:
            names.append(name)
    return tuple(names)


_LC_STOP = {"of", "in", "on", "to", "is", "as", "at", "by", "for", "the", "and", "or", "via", "with", "we"}


def _lowercase_authors(tokens: list[str]) -> tuple[tuple[str, ...], int]:
    """Greedy author list at the start of lower-case, punctuation-free text.

    Tries "surname initials" pairs (``devlin j chang mw``) and "initials surname" pairs
    (``n reimers and i gurevych``) and keeps whichever explains more tokens. Returns the
    surnames and the index of the first token after the author list.
    """
    def is_initials(t: str) -> bool:
        return bool(re.fullmatch(r"[a-z]{1,3}", t)) and t not in _LC_STOP

    def is_surname(t: str) -> bool:
        return len(t) >= 2 and t.isalpha() and t not in _LC_STOP

    def run(surname_first: bool) -> tuple[list[str], int]:
        names, i = [], 0
        while i + 1 < len(tokens):
            if tokens[i] in {"and", "et"}:
                i += 2 if tokens[i] == "et" and tokens[i + 1] == "al" else 1
                continue
            a, b = tokens[i], tokens[i + 1]
            if surname_first and is_surname(a) and is_initials(b):
                names.append(a)
            elif not surname_first and is_initials(a) and is_surname(b) and not is_initials(b):
                names.append(b)
            else:
                break
            i += 2
            if i < len(tokens) and tokens[i] == "and":
                i += 1
        return names, i

    best = max(run(True), run(False), key=lambda r: (r[1], len(r[0])))
    return tuple(best[0]), best[1]


_LC_VENUE = re.compile(
    r"\b(?:in proceedings|proceedings|proc|journal|transactions|advances in|conference|"
    r"workshop|arxiv|preprint|nature|science)\b"
)


def _parse_lowercase(body: str, year: Optional[int]) -> tuple[tuple[str, ...], str, str]:
    """(authors, title, venue) for the lower-case, punctuation-free study format."""
    tokens = body.split()
    authors, i = _lowercase_authors(tokens)
    rest = tokens[i:]
    if rest and year and rest[0].startswith(str(year)):
        rest = rest[1:]  # "vaswani a 2017 attention is all you need"
    text = " ".join(rest)
    if year:
        text = re.sub(rf"\s*\b{year}[a-z]?\b\s*$", "", text)
    m = _LC_VENUE.search(text)
    if m and m.start() > 0:
        return authors, _clean_title(text[:m.start()]), _clean_venue(text[m.start():])
    return authors, _clean_title(text), ""


# ── full parse ────────────────────────────────────────────────────────────────

_QUOTED_TITLE = re.compile(r"[\"“”](.+?)[,.]?[\"“”]")


def _split_sentences(text: str) -> list[str]:
    """Split on '. ', '? ', '! ' except after common bibliographic abbreviations.

    Only used after the author list (APA) or for Vancouver, where an initial or
    "et al." followed by '. ' does end the author list.
    """
    parts, start = [], 0
    for m in re.finditer(r"(?<=[.?!])\s+", text):
        before = text[start:m.start()]
        last = before.split()[-1] if before.split() else ""
        if last.lower() in {"eds.", "ed.", "vol.", "no.", "pp.", "proc.", "conf."}:
            continue
        parts.append(text[start:m.start()].strip())
        start = m.end()
    parts.append(text[start:].strip())
    return [p for p in parts if p]


def _clean_title(title: str) -> str:
    return title.strip().strip(" .,;:\"“”'")


def _clean_venue(venue: str) -> str:
    v = re.sub(rf"\b{_YEAR}[a-z]?\b", " ", venue)
    v = re.sub(r"^\s*(?:in|In)\s*:?\s+", "", v)
    v = re.sub(r"\s+", " ", v).strip(" .,;:")
    return v


def parse_citation(text: str) -> ParsedCitation:
    """Extract structured fields from one citation string."""
    raw = str(text or "")
    cleaned = extract_core_citation(raw)
    doi = find_doi(cleaned)
    arxiv_id = find_arxiv_id(cleaned) or (arxiv_id_from_doi(doi) if doi else None)
    body = re.sub(r"\s+", " ", _strip_identifiers(cleaned)).strip(" .")
    body = re.sub(r"\b(?:Available|Retrieved)\s+(?:at|from)\s*:?\s*$", "", body).strip(" .")
    year = extract_year(body)

    authors: tuple[str, ...] = ()
    title = venue = ""
    style = "freeform"

    qm = _QUOTED_TITLE.search(body)
    apa = re.search(rf"\(\s*{_YEAR}[a-z]?\s*\)\.?", body)
    if qm:  # IEEE / Chicago: authors, "Title," venue, year.
        style = "ieee"
        authors = parse_authors(body[:qm.start()].strip(" ,"))
        title = _clean_title(qm.group(1))
        venue = _clean_venue(body[qm.end():])
    elif apa:  # APA: Authors (Year). Title. Venue.
        style = "apa"
        authors = parse_authors(body[:apa.start()])
        rest = _split_sentences(body[apa.end():].strip())
        if rest:
            title = _clean_title(rest[0])
            venue = _clean_venue(" ".join(rest[1:]))
    elif body.islower() and "," not in body:  # study format: "vaswani a shazeer n 2017 attention ..."
        style = "lowercase"
        authors, title, venue = _parse_lowercase(body, year)
    else:
        sentences = _split_sentences(body)
        if len(sentences) >= 2 and _looks_like_author_list(sentences[0]):
            style = "vancouver"
            authors = parse_authors(sentences[0])
            title = _clean_title(sentences[1])
            venue = _clean_venue(" ".join(sentences[2:]))
        else:
            lead = re.match(r"^([^\W\d_][\w'’\-]+(?:\s+(?:and|&)\s+[^\W\d_][\w'’\-]+)?(?:\s+et\s+al\.?)?)[\s,(]+" + _YEAR, body)
            if lead:
                authors = parse_authors(lead.group(1))
                title = _clean_title(body[lead.end():].lstrip(" ).,"))
    return ParsedCitation(
        raw=raw, cleaned=cleaned, authors=authors, year=year, title=title, venue=venue,
        doi=doi, arxiv_id=arxiv_id, style=style,
    )


def _looks_like_author_list(segment: str) -> bool:
    """Vancouver author list: 'He K, Zhang X, Ren S' — surnames followed by initials."""
    pieces = [p.strip(" .") for p in re.sub(r"\bet\s+al\b", "", segment).split(",") if p.strip(" .")]
    if not pieces:
        return False
    hits = sum(bool(re.fullmatch(r"[^\W\d_][\w'’\- ]*\s[A-Z]{1,3}", p)) for p in pieces)
    return hits >= max(1, len(pieces) // 2)
