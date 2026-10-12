import pytest

from citeverify.clients.http import HttpError
from citeverify.clients.registries import (
    ArxivClient, CrossrefClient, DataCiteClient, DoiOrgClient, _parse_arxiv_feed, clean_markup,
)
from tests.conftest import atom_feed


def test_clean_markup():
    assert clean_markup("Data Via the\n  <i>EM</i> Algorithm &amp; more") == "Data Via the EM Algorithm & more"


def test_crossref_record_merges_subtitle_and_all_dates(registry):
    registry.crossref_work(
        "10.3115/1073083.1073135", "BLEU", ["Papineni", "Roukos"], 2001,
        subtitle=["a method for automatic evaluation of machine translation"],
        **{"published-print": {"date-parts": [[2002, 7]]}},
    )
    rec = CrossrefClient(registry.http).get_work("10.3115/1073083.1073135")
    assert rec.title == "BLEU: a method for automatic evaluation of machine translation"
    assert rec.years == {2001, 2002}
    assert rec.authors == ("Papineni", "Roukos")
    assert rec.url == "https://doi.org/10.3115/1073083.1073135"


def test_crossref_404_and_error(registry):
    registry.crossref_missing("10.1/missing")
    registry.put("https://api.crossref.org/works/10.1/teapot", None, 418)
    cr = CrossrefClient(registry.http)
    assert cr.get_work("10.1/missing") is None
    with pytest.raises(HttpError):
        cr.get_work("10.1/teapot")


def test_crossref_search(registry):
    registry.crossref_search("He 2016 deep residual", [
        {"DOI": "10.1109/CVPR.2016.90", "title": ["Deep Residual Learning"], "author": [{"family": "He"}],
         "issued": {"date-parts": [[2016]]}},
    ])
    hits = CrossrefClient(registry.http).search("He 2016 deep residual")
    assert [h.doi for h in hits] == ["10.1109/CVPR.2016.90"]


def test_datacite(registry):
    registry.datacite_work("10.48550/arXiv.1412.6980", "Adam", ["Kingma", "Ba"], 2014)
    rec = DataCiteClient(registry.http).get_work("10.48550/arXiv.1412.6980")
    assert (rec.source, rec.title, rec.authors, rec.year) == ("DataCite", "Adam", ("Kingma", "Ba"), 2014)
    registry.datacite_missing("10.1/none")
    assert DataCiteClient(registry.http).get_work("10.1/none") is None


def test_arxiv_feed_reads_name_tags_and_skips_error_entries():
    feed = atom_feed(("1706.03762", "Attention Is All\n You Need", ["Ashish Vaswani", "Noam Shazeer"], 2017))
    feed = feed.replace("</feed>", "<entry><id>http://arxiv.org/api/errors#bad</id><title>Error</title></entry></feed>")
    [rec] = _parse_arxiv_feed(feed)
    assert rec.title == "Attention Is All You Need"
    assert rec.authors == ("Vaswani", "Shazeer")  # v1 looked for <n> tags and never found authors
    assert rec.doi == "10.48550/arXiv.1706.03762" and rec.year == 2017


def test_arxiv_malformed_xml():
    with pytest.raises(HttpError):
        _parse_arxiv_feed("<feed")


def test_arxiv_client_get_and_search(registry):
    feed = atom_feed(("1412.6980", "Adam: A Method for Stochastic Optimization", ["Diederik P. Kingma"], 2014))
    registry.arxiv_id("1412.6980", feed)
    registry.arxiv_id("2199.99999", atom_feed())
    registry.arxiv_search("Adam: A method for stochastic optimization", feed)
    ax = ArxivClient(registry.http)
    assert ax.get_work("1412.6980").authors == ("Kingma",)
    assert ax.get_work("2199.99999") is None
    assert len(ax.search_title("Adam: A method for stochastic optimization")) == 1
    assert ax.search_title("!!!") == []
    assert registry.http.min_interval["export.arxiv.org"] == 3.0


def test_query_terms():
    from citeverify.clients.registries import query_terms
    assert query_terms("SciPy 1.0: Fundamental algorithms for scientific computing in Python") == [
        "scipy", "fundamental", "algorithms", "scientific", "computing", "python"]
    assert query_terms("") == []


def test_doi_org_handles(registry):
    registry.handle("10.1/yes", True)
    registry.handle("10.1/no", False)
    d = DoiOrgClient(registry.http)
    assert d.exists("10.1/yes") is True
    assert d.exists("10.1/no") is False
