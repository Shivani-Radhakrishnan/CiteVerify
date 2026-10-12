from citeverify.matching import (
    best_match, title_in_text, check_first_author, check_title, check_year, compare, title_similarity,
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
    m = best_match(p, [rec(title="Something else entirely"), rec()])
    assert m.record.title.startswith("Deep") and m.similarity == 1.0 and m.consistent
    assert best_match(p, []).record is None


def test_best_match_prefers_consistent_record_and_skips_errata():
    p = parse_citation("Lander, E. S. (2001). Initial sequencing and analysis of the human genome. Nature.")
    erratum = rec(title="Erratum: Initial sequencing and analysis of the human genome", authors=("Lander",), years=(2001,))
    other_year = rec(title="Initial sequencing and analysis of the human genome", authors=("Lander",), years=(1999,))
    right = rec(title="Initial sequencing and analysis of the human genome", authors=("Lander",), years=(2001,))
    m = best_match(p, [erratum, other_year, right])
    assert m.record is right and m.consistent
    assert best_match(p, [erratum]).record is None


def test_word_order_matters():
    assert title_similarity("Semi-supervised classification with graph convolutional networks",
                            "Hybrid graph convolutional networks for semi-supervised classification") < 0.85


def test_title_in_text_handles_unparsed_and_dehyphenated_text():
    text = "lewis p perez e 2020 retrievalaugmented generation for knowledgeintensive nlp tasks neurips"
    assert title_in_text("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", text) == 0.95
    assert title_in_text("Random forests", "random forests for traffic forecasting") == 0.0  # too short


def test_group_author_is_not_checked():
    p = parse_citation("Lander, E. S. (2001). Initial sequencing and analysis of the human genome. Nature.")
    r = rec(authors=("International Human Genome Sequencing Consortium",))
    assert check_first_author(p, r).status == "unchecked"


def test_first_author_named_up_front_counts_as_match():
    p = parse_citation("thorne j vlachos a fever a largescale dataset 2018")
    assert check_first_author(p, rec(authors=("Thorne", "Vlachos"))).status == "match"


def test_venue_record_is_not_mistaken_for_the_cited_work():
    p = parse_citation("Peters, M. E. (2018). On the robustness of scalable graph transformers. "
                       "Proceedings of the 2018 Conference of the North American Chapter of the ACL.")
    volume = rec(title="Proceedings of the 2018 Conference of the North American Chapter of the ACL",
                 authors=(), years=(2018,))
    assert best_match(p, [volume]).similarity < 0.6
