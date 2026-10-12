"""Evaluate CiteVerify on citations that language models actually wrote.

    python -m evaluation.run_llm            # replayed from data/llm_citations/http_cache.json
    python -m evaluation.run_llm --record   # re-query the live registries

Labels come from ``evaluation.label_llm_citations`` (OpenAlex-based, independent of
CiteVerify) and were committed before this script was first run. Same systems, threshold
and metrics as ``evaluation.run``.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from citeverify.clients.http import HttpClient, JsonFileCache
from evaluation.run import RESULTS_DIR, metrics, pct, summarise, systems

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "llm_citations"
CITATIONS = DATA / "llm_citations.csv"
CACHE = DATA / "http_cache.json"


def load() -> list[dict]:
    with CITATIONS.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["human_label"] = int(r["human_label"])
    return rows


def render(report: dict) -> str:
    n, fab = report["n_items"], report["n_fabricated"]
    lines = [f"### Citations written by language models ({n}: {n - fab} real, {fab} fabricated)", "",
             "Real citations wrongly flagged (false positives), and fabricated ones caught:", "",
             "| System | Real flagged HALLUCINATED | Real left UNCERTAIN | Fabricated caught (strict) | Fabricated caught (review) |",
             "|---|---|---|---|---|"]
    for name, s in report["systems"].items():
        m, rv = s["overall"]["confusion"], s["review_mode"]["confusion"]
        real_unc = s["labels"]["real"].get("UNCERTAIN", 0)
        lines.append(f"| {name} | {m['fp']}/{n - fab} ({pct(m['fp'] / (n - fab))}) | {real_unc} ({pct(real_unc / (n - fab))}) | "
                     f"{m['tp']}/{fab} | {rv['tp']}/{fab} |")
    lines += ["", "Per model (`v2`): real wrongly flagged / real, fabricated caught / fabricated", "",
              "| Source | Real wrongly flagged | Fabricated caught |", "|---|---|---|"]
    for model, v in report["by_model"].items():
        lines.append(f"| {model} | {v['fp']}/{v['real']} | {v['tp']}/{v['fabricated']} |")
    lines += ["", "Every `v2` error:", "", "| id | truth | category | score | tier |", "|---|---|---|---|---|"]
    for e in report["systems"]["v2"]["errors"]:
        lines.append(f"| {e['id']} | {'fabricated' if e['label'] else 'real'} | {e['category']} | {e['pred_score']:.2f} | {e['tier']} |")
    return "\n".join(lines) + "\n"


def evaluate(record: bool = False) -> dict:
    cache = JsonFileCache(CACHE)
    http = HttpClient(cache=cache, offline=not record, timeout=20, retries=3, backoff=2.0)
    rows = load()
    report: dict = {"n_items": len(rows), "n_fabricated": sum(r["human_label"] for r in rows), "systems": {}}
    outcomes = {}
    try:
        for name, run in systems(http).items():
            if name == "v2_with_table":
                continue
            print(f"  running {name} ...", file=sys.stderr)
            outcomes[name] = run(rows, lambda t: t)
            report["systems"][name] = summarise(outcomes[name])
    finally:
        if record and cache.dirty:
            cache.save()
            print(f"  cache saved: {len(cache)} responses -> {CACHE}", file=sys.stderr)

    by_model = defaultdict(list)
    for o in outcomes["v2"]:
        by_model[o.item["model"]].append(o)
    report["by_model"] = {}
    for model, v in sorted(by_model.items()):
        c = metrics(v)["confusion"]
        report["by_model"][model] = {"real": c["fp"] + c["tn"], "fabricated": c["tp"] + c["fn"], "fp": c["fp"], "tp": c["tp"]}
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)
    report = evaluate(args.record)
    md = render(report)
    print(md)
    if not args.no_save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / "llm.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        (RESULTS_DIR / "llm.md").write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
