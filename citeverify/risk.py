"""Learned, calibrated risk that a citation is fabricated.

The rule-based pipeline decides *what* to check and collects evidence (does the
identifier resolve, how similar is the registry title, does the year or first author
disagree, ...). This module turns that evidence into a feature vector and scores it with
a small model trained by ``evaluation/train_risk.py``. The output is a probability that
the citation is fabricated, calibrated on held-out folds, so "risk 8%" means roughly
one in twelve such citations is fabricated.

The model is stored as plain JSON (feature names, scaling, coefficients and the
calibration parameters); loading it needs no pickle and no scikit-learn.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from citeverify.matching import check_first_author, check_year, content_tokens, title_similarity
from citeverify.models import AuditResult, Tier

MODEL_PATH = Path(__file__).resolve().parent / "data" / "risk_model.json"

_TIERS = {
    Tier.TEMPORAL.value: "tier_temporal",
    Tier.DOI.value: "tier_doi",
    Tier.SEARCH.value: "tier_search",
    Tier.HEURISTIC.value: "tier_heuristic",
    Tier.KNOWN.value: "tier_heuristic",
}
_STATUS = {"match": 1.0, "minor": 0.5, "mismatch": 0.0}

#: Every feature, in model order.
FEATURES = [
    "tier_temporal", "tier_doi", "tier_search", "tier_heuristic",
    "id_given", "id_arxiv", "id_not_registered", "record_found",
    "src_crossref", "src_datacite", "src_arxiv",
    "title_sim", "title_unchecked",
    "year_agree", "year_gap", "year_unchecked",
    "author_agree", "author_unchecked",
    "title_tokens", "n_authors", "has_venue",
    "style_apa", "style_ieee", "style_vancouver", "style_other",
    "registry_error", "rule_score",
]


def features(result: AuditResult) -> dict[str, float]:
    """Numeric evidence for one audited citation (no network access)."""
    f = dict.fromkeys(FEATURES, 0.0)
    p, rec = result.parsed, result.record
    f[_TIERS.get(result.tier, "tier_heuristic")] = 1.0
    if p is not None:
        f["id_given"] = float(bool(p.doi))
        f["id_arxiv"] = float(bool(p.doi and p.doi.lower().startswith("10.48550/")))
        f["title_tokens"] = min(len(content_tokens(p.title)), 20) / 20
        f["n_authors"] = min(len(p.authors), 6) / 6
        f["has_venue"] = float(bool(p.venue))
        style = p.style if p.style in ("apa", "ieee", "vancouver") else "other"
        f[f"style_{style}"] = 1.0
    f["id_not_registered"] = float(result.sub == "DOI does not exist")
    f["registry_error"] = float(bool(result.error))
    f["rule_score"] = float(result.score)
    if rec is not None and p is not None:
        f["record_found"] = 1.0
        f[f"src_{rec.source.lower()}"] = 1.0 if rec.source.lower() in ("crossref", "datacite", "arxiv") else 0.0
        if p.title and rec.title:
            f["title_sim"] = title_similarity(p.title, rec.title)
        else:
            f["title_unchecked"] = 1.0
        yc = check_year(p, rec)
        if yc.status in _STATUS:
            f["year_agree"] = _STATUS[yc.status]
            if p.year is not None and rec.years:
                f["year_gap"] = min(min(abs(p.year - y) for y in rec.years), 5) / 5
        else:
            f["year_unchecked"] = 1.0
        ac = check_first_author(p, rec)
        if ac.status in _STATUS:
            f["author_agree"] = _STATUS[ac.status]
        else:
            f["author_unchecked"] = 1.0
    else:
        f["title_unchecked"] = f["year_unchecked"] = f["author_unchecked"] = 1.0
    return f


@dataclass(frozen=True)
class RiskModel:
    """Standardised logistic regression followed by Platt (sigmoid) calibration."""

    features: tuple[str, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]
    coef: tuple[float, ...]
    intercept: float
    calib_a: float               # calibrated logit = a * raw logit + b
    calib_b: float
    flag_at: float               # risk at or above this: flagged as fabricated
    meta: dict

    @classmethod
    def from_json(cls, data: dict) -> "RiskModel":
        return cls(
            features=tuple(data["features"]), mean=tuple(data["mean"]), scale=tuple(data["scale"]),
            coef=tuple(data["coef"]), intercept=float(data["intercept"]),
            calib_a=float(data["calibration"]["a"]), calib_b=float(data["calibration"]["b"]),
            flag_at=float(data["thresholds"]["flag_at"]),
            meta=data.get("meta", {}),
        )

    def logit(self, f: dict[str, float]) -> float:
        """Uncalibrated log-odds of fabrication."""
        return self.intercept + sum(
            c * ((f.get(name, 0.0) - m) / s) for name, m, s, c in zip(self.features, self.mean, self.scale, self.coef)
        )

    def calibrate(self, logit: float) -> float:
        z = self.calib_a * logit + self.calib_b
        return 1.0 / (1.0 + math.exp(-max(min(z, 40.0), -40.0)))

    def risk(self, result: AuditResult) -> float:
        """Calibrated probability that the citation is fabricated."""
        return self.calibrate(self.logit(features(result)))

    def flagged(self, risk: float) -> bool:
        """Binary decision at the operating point chosen on training folds."""
        return risk >= self.flag_at


@lru_cache(maxsize=1)
def load_model(path: Optional[str] = None) -> Optional[RiskModel]:
    """The shipped model, or ``None`` if it has not been trained yet."""
    p = Path(path) if path else MODEL_PATH
    if not p.exists():
        return None
    return RiskModel.from_json(json.loads(p.read_text(encoding="utf-8")))
