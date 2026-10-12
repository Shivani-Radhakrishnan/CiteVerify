"""Clients for the scholarly registries: Crossref, DataCite, arXiv and the doi.org handle API.

Every client returns :class:`~citeverify.models.WorkRecord` objects (or ``None`` when the
registry says the identifier does not exist) and raises
:class:`~citeverify.clients.http.HttpError` when the registry cannot be reached or answers
with an unexpected status. Payloads are trimmed to the fields the pipeline uses before
they are cached.
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from typing import Any, Optional
from urllib.parse import quote

from citeverify.clients.http import HttpClient, HttpError
from citeverify.models import WorkRecord

_TAG_RE = re.compile(r"<[^>]+>")


def clean_markup(text: str) -> str:
    """Strip JATS/HTML tags and entities that registries embed in titles."""
    text = html.unescape(_TAG_RE.sub("", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _quote_doi(doi: str) -> str:
    return quote(doi, safe="/:;()._-")


# ── Crossref ──────────────────────────────────────────────────────────────────

_CR_DATE_FIELDS = ("published-print", "published-online", "issued", "published")
_CR_KEEP = ("DOI", "title", "subtitle", "author", "container-title", *_CR_DATE_FIELDS)


def _slim_crossref_item(item: dict) -> dict:
    out = {k: item[k] for k in _CR_KEEP if k in item}
    if "author" in out:
        out["author"] = [
            {k: a[k] for k in ("family", "given", "name") if k in a} for a in out["author"]
        ]
    return out


def _crossref_record(item: dict) -> WorkRecord:
    title = clean_markup(" ".join(item.get("title") or []))
    subtitle = clean_markup(" ".join(item.get("subtitle") or []))
    if subtitle and subtitle.lower() not in title.lower():
        title = f"{title}: {subtitle}" if title else subtitle
    years = set()
    for k in _CR_DATE_FIELDS:
        parts = (item.get(k) or {}).get("date-parts") or [[]]
        if parts and parts[0] and parts[0][0]:
            years.add(int(parts[0][0]))
    authors = tuple(
        a.get("family") or a.get("name", "") for a in item.get("author") or [] if a
    )
    doi = item.get("DOI")
    return WorkRecord(
        source="Crossref", title=title, authors=tuple(a for a in authors if a),
        years=frozenset(years), doi=doi,
        venue=clean_markup(" ".join(item.get("container-title") or [])),
        url=f"https://doi.org/{doi}" if doi else "",
    )


class CrossrefClient:
    """Crossref REST API (https://api.crossref.org)."""

    BASE = "https://api.crossref.org/works"

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def get_work(self, doi: str) -> Optional[WorkRecord]:
        """Metadata for ``doi``; ``None`` if Crossref has no such DOI."""
        resp = self.http.get(
            f"{self.BASE}/{_quote_doi(doi)}",
            slim=lambda d: {"message": _slim_crossref_item(d.get("message", {}))},
        )
        if resp.status == 404:
            return None
        if not resp.ok:
            raise HttpError(f"Crossref returned HTTP {resp.status}")
        return _crossref_record(resp.data["message"])

    def search(self, citation: str, rows: int = 10) -> list[WorkRecord]:
        """Best bibliographic matches for a free-text citation.

        Ten rows rather than a handful: errata, reviews and corrections often outrank
        the original work and are filtered out downstream.
        """
        resp = self.http.get(
            self.BASE,
            params={
                "query.bibliographic": citation[:500],
                "rows": rows,
                "select": ",".join(_CR_KEEP),
            },
            slim=lambda d: {"message": {"items": [
                _slim_crossref_item(i) for i in d.get("message", {}).get("items", [])
            ]}},
        )
        if not resp.ok:
            raise HttpError(f"Crossref search returned HTTP {resp.status}")
        return [_crossref_record(i) for i in resp.data["message"]["items"]]


# ── DataCite ──────────────────────────────────────────────────────────────────

def _slim_datacite(d: dict) -> dict:
    a = (d.get("data") or {}).get("attributes") or {}
    return {"data": {"attributes": {
        "doi": a.get("doi"),
        "titles": a.get("titles") or [],
        "creators": [
            {k: c[k] for k in ("familyName", "name") if k in c} for c in a.get("creators") or []
        ],
        "publicationYear": a.get("publicationYear"),
        "publisher": a.get("publisher"),
    }}}


class DataCiteClient:
    """DataCite REST API (https://api.datacite.org). Registers arXiv, Zenodo, etc."""

    BASE = "https://api.datacite.org/dois"

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def get_work(self, doi: str) -> Optional[WorkRecord]:
        resp = self.http.get(f"{self.BASE}/{_quote_doi(doi)}", slim=_slim_datacite)
        if resp.status == 404:
            return None
        if not resp.ok:
            raise HttpError(f"DataCite returned HTTP {resp.status}")
        a = resp.data["data"]["attributes"]
        titles = a.get("titles") or []
        authors = []
        for c in a.get("creators") or []:
            name = c.get("familyName") or (c.get("name") or "").split(",")[0]
            if name.strip():
                authors.append(name.strip())
        year = a.get("publicationYear")
        publisher = a.get("publisher")
        if isinstance(publisher, dict):
            publisher = publisher.get("name", "")
        return WorkRecord(
            source="DataCite",
            title=clean_markup(titles[0].get("title", "")) if titles else "",
            authors=tuple(authors),
            years=frozenset({int(year)}) if year else frozenset(),
            doi=a.get("doi") or doi, venue=publisher or "",
            url=f"https://doi.org/{a.get('doi') or doi}",
        )


# ── arXiv ─────────────────────────────────────────────────────────────────────

_ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_arxiv_feed(xml_text: str) -> list[WorkRecord]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise HttpError("arXiv returned malformed XML") from exc
    records = []
    for entry in root.iter(f"{_ATOM}entry"):
        id_url = (entry.findtext(f"{_ATOM}id") or "").strip()
        title = clean_markup(entry.findtext(f"{_ATOM}title") or "")
        # arXiv reports unknown IDs as an entry titled "Error" with an /api/errors id.
        if "/api/errors" in id_url or not title or title.lower() == "error":
            continue
        published = (entry.findtext(f"{_ATOM}published") or "")[:4]
        authors = []
        for a in entry.findall(f"{_ATOM}author"):
            name = (a.findtext(f"{_ATOM}name") or "").strip()
            if name:
                authors.append(name.split()[-1])
        m = re.search(r"abs/(.+?)(v\d+)?$", id_url)
        arxiv_id = m.group(1) if m else ""
        records.append(WorkRecord(
            source="arXiv", title=title, authors=tuple(authors),
            years=frozenset({int(published)}) if published.isdigit() else frozenset(),
            doi=f"10.48550/arXiv.{arxiv_id}" if arxiv_id else None, venue="arXiv",
            url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else id_url,
        ))
    return records


_QUERY_STOP = {"the", "and", "for", "with", "from", "into", "via", "using", "towards", "toward", "are", "its"}


def query_terms(title: str, limit: int = 8) -> list[str]:
    """Distinctive search terms of a title: words of 3+ letters, minus stop words."""
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", title or "")]
    seen: list[str] = []
    for w in words:
        if w not in _QUERY_STOP and w not in seen:
            seen.append(w)
    return seen[:limit]


def slim_atom(xml_text: str) -> str:
    """Keep only id, title, published date and author names of each feed entry."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return xml_text
    out = ET.Element("feed", xmlns=_ATOM[1:-1])
    for entry in root.iter(f"{_ATOM}entry"):
        e = ET.SubElement(out, "entry")
        for tag in ("id", "title", "published"):
            ET.SubElement(e, tag).text = entry.findtext(f"{_ATOM}{tag}") or ""
        for a in entry.findall(f"{_ATOM}author"):
            ET.SubElement(ET.SubElement(e, "author"), "name").text = a.findtext(f"{_ATOM}name") or ""
    return ET.tostring(out, encoding="unicode")


class ArxivClient:
    """arXiv export API (https://info.arxiv.org/help/api). Asks for 3 s between calls."""

    BASE = "https://export.arxiv.org/api/query"
    MIN_INTERVAL = 3.0

    def __init__(self, http: HttpClient) -> None:
        self.http = http
        self.http.min_interval.setdefault("export.arxiv.org", self.MIN_INTERVAL)

    def _query(self, params: dict[str, Any]) -> list[WorkRecord]:
        resp = self.http.get(self.BASE, params=params, as_json=False, slim=slim_atom)
        if not resp.ok:
            raise HttpError(f"arXiv returned HTTP {resp.status}")
        return _parse_arxiv_feed(resp.data)

    def get_work(self, arxiv_id: str) -> Optional[WorkRecord]:
        records = self._query({"id_list": arxiv_id, "max_results": 1})
        return records[0] if records else None

    def search_title(self, title: str, max_results: int = 5) -> list[WorkRecord]:
        """Works whose title contains every distinctive word of ``title``.

        An AND of title terms is used instead of a quoted phrase because arXiv's phrase
        search is brittle with punctuation and numbers ("SciPy 1.0:").
        """
        terms = query_terms(title)
        if not terms:
            return []
        query = " AND ".join(f"ti:{t}" for t in terms)
        return self._query({"search_query": query, "max_results": max_results})


# ── doi.org handle API ────────────────────────────────────────────────────────

class DoiOrgClient:
    """Existence check against the DOI handle system (covers every registration agency)."""

    BASE = "https://doi.org/api/handles"

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def exists(self, doi: str) -> bool:
        resp = self.http.get(
            f"{self.BASE}/{_quote_doi(doi)}",
            slim=lambda d: {"responseCode": d.get("responseCode")},
        )
        if resp.status == 404:
            return False
        if not resp.ok:
            raise HttpError(f"doi.org returned HTTP {resp.status}")
        return resp.data.get("responseCode") == 1
