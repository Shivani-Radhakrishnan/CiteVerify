"""Train and evaluate the learned risk model (offline, from recorded registry responses).

    python -m evaluation.train_risk

Data
    train  benchmark dev split (134) + citations written by Claude models (605)
    test   benchmark test split (136) + citations written by ChatGPT and Gemini (200)

Model selection uses only out-of-fold predictions on the training data (5-fold,
stratified, grouped by source paper so a paper and its perturbations stay in one fold).
Candidates: logistic regression over a few regularisation strengths, and gradient
boosting as a reference. The chosen model is calibrated with Platt scaling (a sigmoid
over its log-odds) fitted on its out-of-fold scores; with ~60 fabricated training
examples, isotonic calibration overfits into a few steps, including risks of exactly 0. Operating thresholds is also picked on out-of-fold scores: ``flag_at`` is the lowest risk at which out-of-fold
precision of "fabricated" is >= 95%.

Only then are the two test sets scored, once. Writes ``citeverify/data/risk_model.json``,
``evaluation/results/risk.{json,md}`` and ``docs/risk_calibration.png``.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from citeverify import AuditConfig, Auditor
from citeverify.clients.http import HttpClient, JsonFileCache
from citeverify.risk import FEATURES, MODEL_PATH, RiskModel, features

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evaluation" / "results"
FIGURE = ROOT / "docs" / "risk_calibration.png"
SEED = 7
REFERENCE_YEAR = 2026


def _norm(t: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t.lower()).split())


def load_rows() -> list[dict]:
    """Every labelled citation with its audit result, split and group."""
    rows = []
    bench_http = HttpClient(cache=JsonFileCache(ROOT / "data/benchmark/http_cache.json"), offline=True)
    llm_http = HttpClient(cache=JsonFileCache(ROOT / "data/llm_citations/http_cache.json"), offline=True)
    cfg = AuditConfig(current_year=REFERENCE_YEAR, threshold=0.20, use_risk_model=False)
    bench, llm = Auditor(cfg, bench_http), Auditor(cfg, llm_http)
    with open(ROOT / "data/benchmark/benchmark.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            res = bench.audit(r["citation"], r["doi"] or None)
            group = r["id"] if r["source_key"] == "fabricated" else r["source_key"]
            rows.append({"id": r["id"], "source": "benchmark", "split": "train" if r["split"] == "dev" else "test",
                         "y": int(r["human_label"]), "group": f"b:{group}", "result": res})
    with open(ROOT / "data/llm_citations/llm_citations.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            res = llm.audit(r["citation"], r["doi"] or None)
            held_out = r["model"] in ("chatgpt", "gemini")
            rows.append({"id": r["id"], "source": "chatgpt+gemini" if held_out else "claude",
                         "split": "test" if held_out else "train", "y": int(r["human_label"]),
                         "group": "l:" + _norm(r["parsed_title"] or r["citation"])[:80], "result": res})
    for r in rows:
        if r["result"].error:
            raise SystemExit(f"{r['id']}: registry response missing from the recorded cache")
        r["x"] = [features(r["result"])[f] for f in FEATURES]
    return rows


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error with equal-width bins."""
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(total)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def candidates():
    for c in (0.03, 0.1, 0.3, 1.0, 3.0):
        yield f"logreg C={c}", lambda c=c: LogisticRegression(C=c, max_iter=5000, class_weight="balanced")
    yield "gradient boosting", lambda: HistGradientBoostingClassifier(
        max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=SEED)


def out_of_fold(make, X, y, groups, folds) -> np.ndarray:
    oof = np.zeros(len(y))
    for tr, va in folds:
        scaler = StandardScaler().fit(X[tr])
        model = make().fit(scaler.transform(X[tr]), y[tr])
        p = model.predict_proba(scaler.transform(X[va]))[:, 1]
        oof[va] = p
    return oof


def pick_threshold(y: np.ndarray, risk: np.ndarray) -> float:
    for t in np.unique(risk):
        flagged = risk >= t
        if flagged.sum() >= 5 and y[flagged].mean() >= 0.95:
            return float(t)
    return 1.0


def binary(y: np.ndarray, flagged: np.ndarray) -> dict:
    tp, fp = int((flagged & (y == 1)).sum()), int((flagged & (y == 0)).sum())
    fn = int((~flagged & (y == 1)).sum())
    return {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
            "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0, "real_flagged": fp, "real": int((y == 0).sum()),
            "fake_caught": tp, "fake": int((y == 1).sum())}


def scores(y: np.ndarray, p: np.ndarray) -> dict:
    return {"roc_auc": float(roc_auc_score(y, p)), "avg_precision": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)), "ece": ece(y, p)}


def main() -> int:
    rows = load_rows()
    train = [r for r in rows if r["split"] == "train"]
    test = [r for r in rows if r["split"] == "test"]
    X = np.array([r["x"] for r in train], dtype=float)
    y = np.array([r["y"] for r in train])
    groups = np.array([r["group"] for r in train])
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y, groups))

    # 1. model selection on out-of-fold predictions only
    cv = {}
    for name, make in candidates():
        oof = out_of_fold(make, X, y, groups, folds)
        cv[name] = {"log_loss": float(log_loss(y, np.clip(oof, 1e-6, 1 - 1e-6))),
                    "avg_precision": float(average_precision_score(y, oof)), "oof": oof}
        print(f"  {name:20s} OOF log-loss {cv[name]['log_loss']:.4f}  AP {cv[name]['avg_precision']:.4f}", file=sys.stderr)
    logregs = [n for n in cv if n.startswith("logreg")]
    best = min(logregs, key=lambda n: cv[n]["log_loss"])
    C = float(best.split("=")[1])

    # 2. calibration and thresholds from the chosen model's out-of-fold scores
    oof_logit = _logit(cv[best]["oof"])
    platt = LogisticRegression(C=1e6, max_iter=5000).fit(oof_logit.reshape(-1, 1), y)
    a, b = float(platt.coef_[0][0]), float(platt.intercept_[0])
    oof_risk = 1 / (1 + np.exp(-(a * oof_logit + b)))
    flag_at = pick_threshold(y, oof_risk)

    # 3. final model on all training data
    scaler = StandardScaler().fit(X)
    lr = LogisticRegression(C=C, max_iter=5000, class_weight="balanced").fit(scaler.transform(X), y)
    model_json = {
        "features": FEATURES, "mean": scaler.mean_.tolist(), "scale": [float(s) if s > 0 else 1.0 for s in scaler.scale_],
        "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0]),
        "calibration": {"method": "platt", "a": a, "b": b},
        "thresholds": {"flag_at": flag_at},
        "meta": {"trained_on": "benchmark dev split + Claude-written citations", "n_train": int(len(y)),
                 "n_fabricated": int(y.sum()), "selected": best, "sklearn_seed": SEED},
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(model_json, indent=1) + "\n", encoding="utf-8")
    model = RiskModel.from_json(model_json)

    # 4. score the test sets once
    report = {"cv": {n: {k: v for k, v in d.items() if k != "oof"} for n, d in cv.items()}, "selected": best,
              "thresholds": {"flag_at": flag_at},
              "n_train": int(len(y)), "n_train_fabricated": int(y.sum()), "test": {}}
    curves = {}
    for name, subset in (("benchmark test", [r for r in test if r["source"] == "benchmark"]),
                         ("ChatGPT + Gemini", [r for r in test if r["source"] == "chatgpt+gemini"]),
                         ("all test", test)):
        yt = np.array([r["y"] for r in subset])
        risk = np.array([model.risk(r["result"]) for r in subset])
        rule_p = np.array([1.0 - r["result"].score for r in subset])  # rule score read as a risk (uncalibrated)
        report["test"][name] = {
            "n": len(subset), "fabricated": int(yt.sum()),
            "model": scores(yt, risk) | binary(yt, risk >= flag_at),
            "rules": scores(yt, rule_p) | binary(yt, np.array([r["result"].is_flagged for r in subset])),
            "rules_review_mode": binary(yt, np.array([r["result"].label != "VERIFIED" for r in subset]))
                                 | {"sent_for_review": sum(r["result"].label == "UNCERTAIN" for r in subset)},
        }
        curves[name] = (yt, risk, rule_p)
    coefs = sorted(zip(FEATURES, lr.coef_[0]), key=lambda t: -abs(t[1]))
    report["top_features"] = [{"feature": f, "weight": float(w)} for f, w in coefs[:10]]

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "risk.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    md = render(report)
    (RESULTS / "risk.md").write_text(md, encoding="utf-8")
    plot(*curves["all test"])
    print(md)
    return 0


def render(rep: dict) -> str:
    pct = lambda v: f"{100 * v:.1f}%"
    out = [f"### Learned risk model ({rep['selected']}, trained on {rep['n_train']} citations, "
           f"{rep['n_train_fabricated']} fabricated)", "",
           f"Flag threshold chosen on out-of-fold training scores: risk >= {rep['thresholds']['flag_at']:.3f}.", "",
           "Model selection (5-fold out-of-fold, training data only):", "",
           "| Candidate | log-loss | average precision |", "|---|---|---|"]
    for n, d in rep["cv"].items():
        out.append(f"| {n}{' (selected)' if n == rep['selected'] else ''} | {d['log_loss']:.4f} | {d['avg_precision']:.4f} |")
    for name, d in rep["test"].items():
        rv = d["rules_review_mode"]
        out += ["", f"**Test: {name}** ({d['n']} citations, {d['fabricated']} fabricated)", "",
                "| | ROC-AUC | Avg. precision | Brier | ECE | Precision | Recall | F1 | Real flagged |",
                "|---|---|---|---|---|---|---|---|---|"]
        for who, label in (("rules", "rules (v2.2), HALLUCINATED only"), ("model", "learned risk")):
            m = d[who]
            out.append(f"| {label} | {m['roc_auc']:.3f} | {m['avg_precision']:.3f} | {m['brier']:.3f} | {m['ece']:.3f} | "
                       f"{pct(m['precision'])} | {m['fake_caught']}/{m['fake']} | {pct(m['f1'])} | {m['real_flagged']}/{m['real']} |")
        out.append(f"| rules, review mode (UNCERTAIN counts as flagged) | | | | | {pct(rv['precision'])} | "
                   f"{rv['fake_caught']}/{rv['fake']} | {pct(rv['f1'])} | {rv['real_flagged']}/{rv['real']} "
                   f"({rv['sent_for_review']} sent for review) |")
    out += ["", "Largest weights (standardised features; positive = more likely fabricated):", "",
            "| Feature | Weight |", "|---|---|"]
    out += [f"| `{f['feature']}` | {f['weight']:+.2f} |" for f in rep["top_features"]]
    return "\n".join(out) + "\n"


def plot(y: np.ndarray, risk: np.ndarray, rule_p: np.ndarray) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4.2), dpi=150)
    edges = np.linspace(0, 1, 11)
    for p, label, style in ((rule_p, "rule score (1 - score)", "s--"), (risk, "learned risk (calibrated)", "o-")):
        xs, ys, ns = [], [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
            if m.sum() >= 3:
                xs.append(p[m].mean())
                ys.append(y[m].mean())
                ns.append(int(m.sum()))
        ax.plot(xs, ys, style, label=label, markersize=5)
        if p is risk:  # citations per bin: most predictions are near 0 or 1
            for x, yy, n in zip(xs, ys, ns):
                ax.annotate(f"n={n}", (x, yy), textcoords="offset points", xytext=(6, -12), fontsize=7)
    ax.plot([0, 1], [0, 1], color="0.7", lw=1, label="perfect calibration")
    ax.set_xlabel("predicted probability of fabrication")
    ax.set_ylabel("observed share fabricated")
    ax.set_title(f"Calibration on held-out test data (n={len(y)}, bins of width 0.1)", fontsize=10)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE)


if __name__ == "__main__":
    raise SystemExit(main())
