import pytest

from citeverify.parsing import (
    arxiv_id_from_doi, extract_core_citation, extract_year, find_arxiv_id, find_doi, fold,
    normalise_doi, parse_authors, parse_citation,
)


@pytest.mark.parametrize("raw, expected", [
    ("10.1109/CVPR.2016.90", "10.1109/CVPR.2016.90"),
    ("  doi:10.1109/CVPR.2016.90 ", "10.1109/CVPR.2016.90"),
    ("DOI: 10.1109/CVPR.2016.90", "10.1109/CVPR.2016.90"),
    ("https://doi.org/10.1109/CVPR.2016.90", "10.1109/CVPR.2016.90"),
    ("http://dx.doi.org/10.1109/CVPR.2016.90", "10.1109/CVPR.2016.90"),
    ("doi.org/10.1038/nature14236.", "10.1038/nature14236"),
    ("https://doi.org/10.1016/S0022-2836%2805%2980360-2", "10.1016/S0022-2836(05)80360-2"),
    ("(10.1016/S0022-2836(05)80360-2)", None),  # leading bracket is not part of a DOI
    ("10.1016/S0022-2836(05)80360-2)", "10.1016/S0022-2836(05)80360-2"),
    ("not a doi", None),
    ("", None),
    (None, None),
    ("11.1234/abc", None),
])
def test_normalise_doi(raw, expected):
    assert normalise_doi(raw) == expected


def test_find_doi_in_running_text():
    text = "He, K. (2016). Deep residual learning. CVPR. https://doi.org/10.1109/CVPR.2016.90."
    assert find_doi(text) == "10.1109/CVPR.2016.90"
    assert find_doi("no identifier here") is None


@pytest.mark.parametrize("doi, expected", [
    ("10.48550/arXiv.1706.03762", "1706.03762"),
    ("10.48550/ARXIV.1706.03762v5", "1706.03762"),
    ("10.48550/arXiv.hep-th/9901001", "hep-th/9901001"),
    ("10.1109/CVPR.2016.90", None),
])
def test_arxiv_id_from_doi(doi, expected):
    assert arxiv_id_from_doi(doi) == expected


def test_find_arxiv_id():
    assert find_arxiv_id("Vaswani et al. arXiv:1706.03762v5, 2017") == "1706.03762"
    assert find_arxiv_id("see https://arxiv.org/abs/2005.14165") == "2005.14165"
    assert find_arxiv_id("no id") is None


@pytest.mark.parametrize("text, year", [
    ("He, K. (2016). Deep residual learning.", 2016),
    ("Smith, J. (2020a). Title.", 2020),
    ('K. He, "Deep residual learning," in Proc. CVPR, 2016.', 2016),
    ("Hochreiter S. Long short-term memory. Neural Comput. 9(8), 1735-1780. 1997.", 1997),
    ("Hochreiter S. Long short-term memory. Neural Comput. 1997;9:1735–1780.", 1997),
    ("Some title. doi:10.1109/TPAMI.2019.2913372", None),
    ("vaswani a 2017 attention is all you need", 2017),
    ("no year at all", None),
])
def test_extract_year(text, year):
    assert extract_year(text) == year


@pytest.mark.parametrize("segment, names", [
    ("He, K., Zhang, X., Ren, S., & Sun, J.", ("He", "Zhang", "Ren", "Sun")),
    ("K. He, X. Zhang, S. Ren, and J. Sun", ("He", "Zhang", "Ren", "Sun")),
    ("He K, Zhang X, Ren S, Sun J", ("He", "Zhang", "Ren", "Sun")),
    ("Harris, C. R., Millman, K. J., van der Walt, S. J., et al.", ("Harris", "Millman", "van der Walt")),
    ("Zhu, J.-Y., Park, T.", ("Zhu", "Park")),
    ("J.-Y. Zhu and T. Park", ("Zhu", "Park")),
    ("Barabási, A.-L., & Albert, R.", ("Barabási", "Albert")),
    ("O. Russakovsky et al.", ("Russakovsky",)),
    ("vaswani a shazeer n", ("vaswani", "shazeer")),
])
def test_parse_authors(segment, names):
    assert parse_authors(segment) == names


def test_parse_apa():
    p = parse_citation("Kahneman, D., & Tversky, A. (1979). Prospect theory: An analysis of decision "
                       "under risk. Econometrica, 47(2), 263-291.")
    assert p.style == "apa"
    assert p.authors == ("Kahneman", "Tversky")
    assert p.year == 1979
    assert p.title == "Prospect theory: An analysis of decision under risk"
    assert p.venue.startswith("Econometrica")


def test_parse_ieee():
    p = parse_citation('K. He, X. Zhang, S. Ren, and J. Sun, "Deep residual learning for image '
                       'recognition," in Proc. IEEE CVPR, 2016, pp. 770-778.')
    assert p.style == "ieee"
    assert p.first_author == "He"
    assert p.year == 2016
    assert p.title == "Deep residual learning for image recognition"


def test_parse_vancouver_with_et_al():
    p = parse_citation("Jumper J, Evans R, Pritzel A, et al. Highly accurate protein structure "
                       "prediction with AlphaFold. Nature. 2021.")
    assert p.style == "vancouver"
    assert p.authors == ("Jumper", "Evans", "Pritzel")
    assert p.title == "Highly accurate protein structure prediction with AlphaFold"
    assert p.year == 2021


def test_parse_question_mark_title():
    p = parse_citation("Bender, E. M., & Gebru, T. (2021). On the dangers of stochastic parrots: "
                       "Can language models be too big? FAccT.")
    assert p.title.endswith("too big?")


def test_parse_lowercase_study_format():
    p = parse_citation("vaswani a shazeer n 2017 attention is all you need")
    assert p.style == "lowercase"
    assert p.authors == ("vaswani", "shazeer")
    assert p.title == "attention is all you need"


def test_parse_inline_mention():
    p = parse_citation("As shown by Geiping et al. 2025 or null")
    assert p.cleaned == "Geiping et al. 2025 or null"
    assert p.first_author == "Geiping"
    assert p.year == 2025


def test_parse_extracts_identifiers():
    p = parse_citation("Vaswani, A. (2017). Attention is all you need. arXiv:1706.03762")
    assert p.arxiv_id == "1706.03762"
    assert p.title == "Attention is all you need"


@pytest.mark.parametrize("text, core", [
    ("As shown by Smith et al. 2020, which improves X", "Smith et al. 2020"),
    ("according to Lee 2019", "Lee 2019"),
    ("[12] Lee, K. (2019). Title.", "Lee, K. (2019). Title."),
    ("  see also   Lee 2019 ", "Lee 2019"),
])
def test_extract_core_citation(text, core):
    assert extract_core_citation(text) == core


def test_fold():
    assert fold("Barabási: Émergence—of <i>Scaling</i>!") == "barabasi emergence of i scaling i"


def test_title_keeps_abbreviations_and_drops_bracketed_notes():
    p = parse_citation("Chetty, R., Friedman, J. N., & Olsen, T. (2014). Active vs. passive decisions and crowd-out "
                       "in retirement savings accounts: Evidence from Denmark. The Quarterly Journal of Economics.")
    assert p.title.startswith("Active vs. passive decisions") and p.title.endswith("Evidence from Denmark")
    p = parse_citation("Smith, J. (2020). Heat waves in U.S. cities. Urban Climate, 31.")
    assert p.title == "Heat waves in U.S. cities"
    p = parse_citation("Gottesman, D. (1997). Stabilizer codes and quantum error correction [Doctoral dissertation, Caltech].")
    assert p.title == "Stabilizer codes and quantum error correction"
    # Vancouver initials still end the author list.
    assert parse_citation("Cox DR. Regression models and life-tables. J R Stat Soc B. 1972.").title == "Regression models and life-tables"


def test_arxiv_id_from_doi_field():
    from citeverify.parsing import arxiv_id_from_field
    assert arxiv_id_from_field("arXiv:2210.09421") == "2210.09421"
    assert arxiv_id_from_field("2210.09421v2") == "2210.09421"
    assert arxiv_id_from_field("https://arxiv.org/abs/1706.03762") == "1706.03762"
    assert arxiv_id_from_field("arXiv:quant-ph/9705052") == "quant-ph/9705052"
    assert arxiv_id_from_field("10.1109/CVPR.2016.90") is None
