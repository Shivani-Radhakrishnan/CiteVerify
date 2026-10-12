"""Tier routing and verdicts of the full pipeline, with every registry response mocked."""
from citeverify import Tier
from citeverify.detectors import heuristics, known_papers
from tests.conftest import atom_feed

HE = "He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. CVPR."
HE_DOI = "10.1109/CVPR.2016.90"


def he_record(registry, **kw):
    registry.crossref_work(HE_DOI, "Deep Residual Learning for Image Recognition", ["He", "Zhang"], 2016, **kw)


def tiers(result):
    return [(s.tier.value, s.status) for s in result.trace]


# ── temporal ──────────────────────────────────────────────────────────────────

def test_future_year_is_rejected_even_with_a_doi(make_auditor):
    r = make_auditor().audit(HE.replace("2016", "2031"), HE_DOI)  # no registry call registered
    assert r.label == "HALLUCINATED" and r.tier == Tier.TEMPORAL.value
    assert tiers(r) == [("Temporal check", "decided")]


def test_next_year_is_allowed(make_auditor, registry):
    he_record(registry, **{"published-online": {"date-parts": [[2027]]}})
    r = make_auditor().audit(HE.replace("2016", "2027"), HE_DOI)
    assert r.tier == Tier.DOI.value and r.label == "VERIFIED"


# ── DOI tier ──────────────────────────────────────────────────────────────────

def test_doi_verified(make_auditor, registry):
    he_record(registry)
    r = make_auditor().audit(HE, f"https://doi.org/{HE_DOI}")
    assert r.label == "VERIFIED" and r.tier == "DOI registry"
    assert r.record.doi == HE_DOI
    assert {s.name: s.status for s in r.signals}["Title"] == "pass"


def test_doi_written_in_the_text_is_used(make_auditor, registry):
    he_record(registry)
    r = make_auditor().audit(f"{HE} doi:{HE_DOI}")
    assert r.tier == "DOI registry" and r.label == "VERIFIED"


def test_doi_that_does_not_exist(make_auditor, registry):
    registry.crossref_missing("10.1145/9790000.9790000")
    registry.datacite_missing("10.1145/9790000.9790000")
    registry.handle("10.1145/9790000.9790000", exists=False)
    r = make_auditor().audit(HE, "10.1145/9790000.9790000")
    assert r.label == "HALLUCINATED" and r.sub == "DOI does not exist"


def test_doi_registered_with_another_agency_is_not_called_fake(make_auditor, registry):
    registry.crossref_missing("10.11501/123")
    registry.datacite_missing("10.11501/123")
    registry.handle("10.11501/123", exists=True)
    r = make_auditor().audit(HE, "10.11501/123")
    assert r.label == "UNCERTAIN" and r.sub == "DOI registered elsewhere"


def test_doi_found_in_datacite_after_crossref_404(make_auditor, registry):
    registry.crossref_missing("10.5281/zenodo.1")
    registry.datacite_work("10.5281/zenodo.1", "Deep residual learning for image recognition", ["He"], 2016)
    r = make_auditor().audit(HE, "10.5281/zenodo.1")
    assert r.label == "VERIFIED" and r.record.source == "DataCite"


def test_doi_swap_is_caught(make_auditor, registry):
    registry.crossref_work("10.1023/A:1010933404324", "Random Forests", ["Breiman"], 2001)
    r = make_auditor().audit(HE, "10.1023/A:1010933404324")
    assert r.label == "HALLUCINATED" and r.sub == "DOI exists but details do not match"
    assert "Random Forests" in r.explanation


def test_wrong_year_and_wrong_author(make_auditor, registry):
    he_record(registry)
    assert make_auditor().audit(HE.replace("2016", "2012"), HE_DOI).label == "HALLUCINATED"
    assert make_auditor().audit(HE.replace("He, K.", "Halvorsen, K."), HE_DOI).label == "HALLUCINATED"


def test_off_by_one_year_needs_review_not_rejection(make_auditor, registry):
    he_record(registry)
    r = make_auditor().audit(HE.replace("2016", "2017"), HE_DOI)
    assert r.label == "UNCERTAIN" and r.verdict == "Likely real"


def test_bare_doi_with_no_text_to_compare(make_auditor, registry):
    he_record(registry)
    r = make_auditor().audit("2016", HE_DOI)
    assert r.label == "UNCERTAIN" and "too little text" in r.sub


def test_registry_outage_is_reported_not_guessed(make_auditor):
    r = make_auditor().audit(HE, HE_DOI)  # nothing registered -> offline cache miss
    assert r.label == "UNCERTAIN" and r.sub == "Registry unreachable" and r.error


def test_arxiv_doi_routes_to_datacite_then_arxiv(make_auditor, registry):
    doi = "10.48550/arXiv.1412.6980"
    registry.datacite_missing(doi)
    registry.arxiv_id("1412.6980", atom_feed(
        ("1412.6980", "Adam: A Method for Stochastic Optimization", ["Diederik P. Kingma", "Jimmy Ba"], 2014)))
    r = make_auditor().audit("Kingma, D. P., & Ba, J. (2014). Adam: A method for stochastic optimization. arXiv.", doi)
    assert r.label == "VERIFIED" and r.record.source == "arXiv"


def test_nonexistent_arxiv_id(make_auditor, registry):
    doi = "10.48550/arXiv.2109.95555"
    registry.datacite_missing(doi)
    registry.arxiv_id("2109.95555", atom_feed())
    r = make_auditor().audit("Holm, A. (2021). Sparse neural operators. arXiv.", doi)
    assert r.label == "HALLUCINATED" and r.sub == "DOI does not exist"


def test_invalid_doi_field_is_ignored_with_a_warning(make_auditor, registry):
    registry.crossref_search(HE, [])
    registry.arxiv_search("Deep residual learning for image recognition", atom_feed())
    r = make_auditor().audit(HE, "not-a-doi")
    assert any(s.name == "DOI field" and s.status == "warn" for s in r.signals)
    assert r.tier == "Registry search"


# ── search tier ───────────────────────────────────────────────────────────────

CR_HE = {"DOI": HE_DOI, "title": ["Deep Residual Learning for Image Recognition"],
         "author": [{"family": "He"}, {"family": "Zhang"}], "issued": {"date-parts": [[2016]]}}


def test_search_verifies_a_citation_without_doi(make_auditor, registry):
    registry.crossref_search(HE, [CR_HE])
    r = make_auditor().audit(HE)
    assert r.label == "VERIFIED" and r.tier == "Registry search" and r.record.doi == HE_DOI
    assert ("DOI registry", "skipped") in tiers(r)


def test_search_falls_back_to_arxiv(make_auditor, registry):
    text = "Kingma, D. P., & Ba, J. (2014). Adam: A method for stochastic optimization. arXiv preprint."
    registry.crossref_search(text, [])
    registry.arxiv_search("Adam: A method for stochastic optimization", atom_feed(
        ("1412.6980", "Adam: A Method for Stochastic Optimization", ["Diederik P. Kingma"], 2014)))
    r = make_auditor().audit(text)
    assert r.label == "VERIFIED" and r.record.source == "arXiv"


def test_search_finds_nothing(make_auditor, registry):
    text = "Holm, A. (2020). Sparse neural operators for soil moisture estimation. Neural Networks."
    registry.crossref_search(text, [CR_HE])
    registry.arxiv_search("Sparse neural operators for soil moisture estimation", atom_feed())
    r = make_auditor().audit(text)
    assert r.label == "HALLUCINATED" and r.sub == "No matching record found"
    # the not-found score is configurable; above the threshold it becomes "needs review"
    r2 = make_auditor(not_found_score=0.3).audit(text)
    assert r2.label == "UNCERTAIN"


def test_search_detects_misattributed_title(make_auditor, registry):
    text = "Breiman, L. (2001). Deep residual learning for image recognition. CVPR."
    registry.crossref_search(text, [CR_HE])
    r = make_auditor().audit(text)
    assert r.label == "HALLUCINATED" and r.sub == "Title exists but is credited differently"


def test_search_outage_falls_back_to_heuristics(make_auditor):
    r = make_auditor().audit(HE)
    assert r.tier == "Plausibility heuristics" and r.error
    assert ("Registry search", "skipped") in tiers(r)


def test_search_disabled_uses_heuristics(make_auditor):
    r = make_auditor(use_search=False).audit(HE)
    assert r.tier == "Plausibility heuristics" and r.error is None
    assert r.label != "VERIFIED"  # heuristics never verify


def test_short_inline_mention_skips_search(make_auditor):
    r = make_auditor().audit("as shown by Geiping et al. 2025 or null")
    assert r.tier == "Plausibility heuristics"


# ── legacy table ──────────────────────────────────────────────────────────────

def test_known_papers_table_is_off_by_default(make_auditor, registry):
    text = "devlin j 2019 bert pretraining of deep bidirectional transformers"
    registry.crossref_search(text, [{"DOI": "10.18653/v1/N19-1423",
                                     "title": ["BERT: Pre-training of Deep Bidirectional Transformers"],
                                     "author": [{"family": "Devlin"}], "issued": {"date-parts": [[2019]]}}])
    assert make_auditor().audit(text).label == "VERIFIED"
    # switching the table on flags this genuine paper as fake
    r = make_auditor(use_known_papers=True).audit(text)
    assert r.tier == "Known-papers table (legacy)" and r.label == "HALLUCINATED"


def test_known_papers_lookup_rule():
    assert known_papers.lookup("vaswani a 2017 attention is all you need") == 0.85
    assert known_papers.lookup("vaswani a 2018 attention is all you need") is None
    assert known_papers.lookup("devlin j 2019 bert pretraining of deep transformers") == 0.05
    # two-letter keys can never match: the rule skips words shorter than three letters
    assert known_papers.lookup("ji z 2023 survey of hallucination") is None
    assert known_papers.lookup("") is None


# ── heuristics ────────────────────────────────────────────────────────────────

HEURISTIC_SAMPLES = [
    "geiping et al 2025 or null",
    "vaswani a shazeer n 2017 attention is all you need neurips",
    "As shown by Smith et al. 2020a and Lee 2019b, the",
    "2019 some title without an author",
    "He, K., Zhang, X. (2016). Deep residual learning for image recognition. CVPR.",
]


def test_heuristics_reproduce_the_v1_scorer_exactly():
    from evaluation.baselines import legacy_auditor as v1
    for text in HEURISTIC_SAMPLES:
        assert heuristics.extract_features(text) == v1.extract_citation_features(text)
        assert heuristics.plausibility_score(heuristics.extract_features(text)) == v1.compute_plausibility_score(text)


def test_heuristic_features_and_score():
    f = heuristics.extract_features("geiping et al 2025 or null")
    assert f["ends_connective"] and f["short_fragment"]
    assert heuristics.check("as shown by smith 2020a and lee 2019b and").score == heuristics.MAX_HEURISTIC_SCORE
    assert heuristics.plausibility_score({}) == 0.3
    assert heuristics.extract_features("") == {}


# ── result object ─────────────────────────────────────────────────────────────

def test_label_respects_threshold(make_auditor, registry):
    he_record(registry)
    r = make_auditor(threshold=0.6).audit(HE.replace("2016", "2017"), HE_DOI)  # score 0.5
    assert r.label == "HALLUCINATED"


def test_audit_many_preserves_order(make_auditor, registry):
    he_record(registry)
    items = [(HE, HE_DOI), (HE.replace("2016", "2031"), None), (HE, HE_DOI)]
    labels = [r.label for r in make_auditor().audit_many(items, max_workers=3)]
    assert labels == ["VERIFIED", "HALLUCINATED", "VERIFIED"]


def test_to_row(make_auditor, registry):
    he_record(registry)
    row = make_auditor().audit(HE, HE_DOI).to_row()
    assert row["label"] == "VERIFIED" and row["matched_doi"] == HE_DOI and row["error"] == ""
