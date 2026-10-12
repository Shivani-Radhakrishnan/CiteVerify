"""Shared fixtures: an offline HTTP client whose responses the test registers up front."""
from __future__ import annotations

from typing import Any, Optional

import pytest

from citeverify import AuditConfig, Auditor
from citeverify.clients.http import HttpClient, MemoryCache, cache_key
from citeverify.clients.registries import _quote_doi


class FakeRegistry:
    """Registers canned registry responses in an offline :class:`HttpClient`'s cache.

    Any request the test did not register raises ``OfflineCacheMiss`` — the same error a
    real outage produces — so tests also exercise the pipeline's error handling.
    """

    def __init__(self) -> None:
        self.cache = MemoryCache()
        self.http = HttpClient(cache=self.cache, offline=True)

    def put(self, url: str, data: Any = None, status: int = 200, params: Optional[dict] = None) -> None:
        self.cache.set(cache_key(url, params), {"status": status, "data": data})

    # Crossref ─────────────────────────────────────────────────────────────
    def crossref_work(self, doi: str, title: str, family: list[str], year: int,
                      status: int = 200, **extra: Any) -> None:
        item = {"DOI": doi, "title": [title], "author": [{"family": f} for f in family],
                "issued": {"date-parts": [[year]]}, **extra}
        self.put(f"https://api.crossref.org/works/{_quote_doi(doi)}",
                 {"message": item} if status == 200 else None, status)

    def crossref_missing(self, doi: str) -> None:
        self.put(f"https://api.crossref.org/works/{_quote_doi(doi)}", None, 404)

    def crossref_search(self, query: str, items: list[dict]) -> None:
        from citeverify.clients.registries import _CR_KEEP
        self.put("https://api.crossref.org/works", {"message": {"items": items}},
                 params={"query.bibliographic": query[:500], "rows": 10, "select": ",".join(_CR_KEEP)})

    # DataCite / doi.org / arXiv ────────────────────────────────────────────
    def datacite_work(self, doi: str, title: str, family: list[str], year: int) -> None:
        self.put(f"https://api.datacite.org/dois/{_quote_doi(doi)}", {"data": {"attributes": {
            "doi": doi, "titles": [{"title": title}],
            "creators": [{"familyName": f} for f in family], "publicationYear": year,
        }}})

    def datacite_missing(self, doi: str) -> None:
        self.put(f"https://api.datacite.org/dois/{_quote_doi(doi)}", None, 404)

    def handle(self, doi: str, exists: bool) -> None:
        url = f"https://doi.org/api/handles/{_quote_doi(doi)}"
        if exists:
            self.put(url, {"responseCode": 1})
        else:
            self.put(url, None, 404)

    def arxiv_search(self, title: str, feed: str) -> None:
        from citeverify.clients.registries import query_terms
        query = " AND ".join(f"ti:{t}" for t in query_terms(title))
        self.put("https://export.arxiv.org/api/query", feed,
                 params={"search_query": query, "max_results": 5})

    def arxiv_id(self, arxiv_id: str, feed: str) -> None:
        self.put("https://export.arxiv.org/api/query", feed,
                 params={"id_list": arxiv_id, "max_results": 1})


def atom_feed(*entries: tuple[str, str, list[str], int]) -> str:
    """Minimal arXiv Atom feed. Each entry is (arxiv_id, title, author full names, year)."""
    body = []
    for arxiv_id, title, names, year in entries:
        authors = "".join(f"<author><name>{n}</name></author>" for n in names)
        body.append(
            f"<entry><id>http://arxiv.org/abs/{arxiv_id}v1</id><title>{title}</title>"
            f"<published>{year}-01-01T00:00:00Z</published>{authors}</entry>"
        )
    return ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            "<title>arXiv Query</title>" + "".join(body) + "</feed>")


@pytest.fixture
def registry() -> FakeRegistry:
    return FakeRegistry()


@pytest.fixture
def make_auditor(registry: FakeRegistry):
    def _make(**config: Any) -> Auditor:
        config.setdefault("current_year", 2026)
        return Auditor(AuditConfig(**config), registry.http)
    return _make
