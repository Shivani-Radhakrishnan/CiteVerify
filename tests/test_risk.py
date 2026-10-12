"""The learned risk model: JSON format, features, and the published held-out numbers."""
import json
import math

import numpy as np

from citeverify.models import AuditResult, ParsedCitation, WorkRecord
from citeverify.risk import FEATURES, MODEL_PATH, features, load_model
from evaluation.run import RESULTS_DIR
from tests.test_pipeline import HE, HE_DOI, he_record


def test_shipped_model_loads_without_scikit_learn():
    data = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    assert data["features"] == FEATURES
    assert len(data["coef"]) == len(FEATURES) == len(data["mean"]) == len(data["scale"])
    model = load_model()
    assert model is not None and 0 < model.flag_at < 1


def test_features_without_a_record():
    r = AuditResult(verdict="", sub="", tier="Plausibility heuristics", explanation="", action="", score=0.3,
                    parsed=ParsedCitation(raw="x", cleaned="x"))
    f = features(r)
    assert set(f) == set(FEATURES) and f["tier_heuristic"] == 1.0 and f["title_unchecked"] == 1.0


def test_features_with_a_matching_record():
    p = ParsedCitation(raw="x", cleaned="x", authors=("He",), year=2016, title="Deep residual learning for image recognition",
                       doi=HE_DOI, style="apa")
    rec = WorkRecord(source="Crossref", title="Deep Residual Learning for Image Recognition", authors=("He",),
                     years=frozenset({2016}), doi=HE_DOI)
    f = features(AuditResult(verdict="", sub="", tier="DOI registry", explanation="", action="", score=0.97,
                             parsed=p, record=rec))
    assert f["record_found"] == 1 and f["src_crossref"] == 1 and math.isclose(f["title_sim"], 1.0)
    assert f["year_agree"] == 1 and f["author_agree"] == 1 and f["year_gap"] == 0


def test_risk_is_low_for_a_confirmed_citation_and_high_for_a_contradicted_one(make_auditor, registry):
    he_record(registry)
    good = make_auditor().audit(HE, HE_DOI)
    bad = make_auditor().audit(HE.replace("2016", "2019"), HE_DOI)
    assert good.risk is not None and bad.risk is not None
    assert good.risk < 0.05 < 0.5 < bad.risk


def test_risk_can_be_switched_off(make_auditor, registry):
    he_record(registry)
    assert make_auditor(use_risk_model=False).audit(HE, HE_DOI).risk is None


def test_published_risk_results_reproduce_offline():
    from evaluation import train_risk as T
    published = json.loads((RESULTS_DIR / "risk.json").read_text(encoding="utf-8"))
    model = load_model()
    rows = [r for r in T.load_rows() if r["split"] == "test"]
    for name, sel in (("benchmark test", "benchmark"), ("ChatGPT + Gemini", "chatgpt+gemini")):
        subset = [r for r in rows if r["source"] == sel]
        y = np.array([r["y"] for r in subset])
        risk = np.array([model.risk(r["result"]) for r in subset])
        m = T.binary(y, risk >= model.flag_at)
        want = published["test"][name]["model"]
        assert (m["fake_caught"], m["real_flagged"]) == (want["fake_caught"], want["real_flagged"]), name
