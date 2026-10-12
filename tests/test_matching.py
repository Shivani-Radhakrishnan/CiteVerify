from citeverify.matching import (
    best_match, check_first_author, check_title, check_year, compare, title_similarity,
)
from citeverify.models import WorkRecord
from citeverify.parsing import parse_citation


def rec(title="Deep residual learning for image recognition", authors=("He", "Zhang"), years=(2016,), **kw):
    return WorkRecord(source="Crossref", title=title, authors=tuple(authors), years=frozenset(years), **kw)


def test_title_similarity_ignores_case_punctuation_accents():
    assert title_similarity("Deep Residual Learning for Image Recognition.",
                            "deep residual learning for image recognition") == 1.0
    assert title_similarity("Émergence of scaling", "Emergence of Scaling") == 1.0


def test_title_similarity_handles_subtitles_and_prefixes():
    assert title_similarity("Computing machinery and intelligence",
                            "I.—COMPUTING MACHINERY AND INTELLIGENCE") > 0.85
    assert title_similarity("Maximum likelihood from incomplete data via the EM algorithm",
                            "Maximum Likelihood from Incomplete Data Via the <i>EM</i> Algorithm") > 0.85


def test_title_similarity_separates_different_papers():
    assert title_similarity("Random forests", "Support-vector networks") < 0.6
    assert title_similarity("Towards robust graph transformers for traffic forecasting",
                            "Deep residual learning for image recognition") < 0.6
    assert title_similarity("", "anything") == 0.0


def test_check_title():
    p = parse_citation("He, K. (2016). Deep residual learning for image recognition. CVPR.")
    assert check_title(p, rec()).status == "match"
    assert check_title(p, rec(title="Support-vector networks")).status == "mismatch"
    assert check_title(parse_citation("He 2016"), rec()).status == "unchecked"


def test_check_year_uses_every_registry_date():
    p = parse_citation("Schmidhuber, J. (2014). Deep learning in neural networks. Neural Networks.")
    assert check_year(p, rec(years=(2014, 2015))).status == "match"
    assert check_year(p, rec(years=(2015,))).status == "minor"
    assert check_year(p, rec(years=(2018,))).status == "mismatch"
    assert check_year(p, rec(years=())).status == "unchecked"
    assert check_year(parse_citation("Title only"), rec()).status == "unchecked"


def test_check_first_author():
    p = parse_citation("Harris, C. R., & van der Walt, S. (2020). Array programming with NumPy. Nature.")
    assert check_first_author(p, rec(authors=("Harris", "Millman"))).status == "match"
    assert check_first_author(p, rec(authors=("Millman", "Harris"))).status == "minor"
    assert check_first_author(p, rec(authors=("Oliphant",))).status == "mismatch"
    assert check_first_author(p, rec(authors=())).status == "unchecked"
    # particles and diacritics: arXiv reports only the last token of a name
    q = parse_citation("van der Maaten, L. (2008). Visualizing data using t-SNE. JMLR.")
    assert check_first_author(q, rec(authors=("Maaten",))).status == "match"
    b = parse_citation("Barabási, A.-L. (1999). Emergence of scaling. Science.")
    assert check_first_author(b, rec(authors=("Barabasi",))).status == "match"


def test_compare_returns_three_checks_and_signals():
    p = parse_citation("He, K. (2016). Deep residual learning for image recognition. CVPR.")
    checks = compare(p, rec())
    assert [c.field for c in checks] == ["Title", "Year", "First author"]
    assert all(c.to_signal().status == "pass" for c in checks)


def test_best_match():
    p = parse_citation("He, K. (2016). Deep residual learning for image recognition. CVPR.")
    best, sim = best_match(p, [rec(title="Something else entirely"), rec()])
    assert best.title.startswith("Deep") and sim == 1.0
    assert best_match(p, []) == (None, 0.0)
