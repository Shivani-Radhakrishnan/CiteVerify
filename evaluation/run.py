"""Evaluate CiteVerify on the held-out benchmark, offline and reproducibly.

    python -m evaluation.run                  # test split, all systems, replayed from cache
    python -m evaluation.run --split dev      # development split
    python -m evaluation.run --record         # re-query the live APIs and refresh the cache

Every registry response the systems need is stored in ``data/benchmark/http_cache.json``.
Replay mode never touches the network: a request missing from the cache aborts the run.

Systems compared:

    v1                 original engine (frozen copy), known-papers table on, as shipped
    v1_no_table        original engine with the known-papers table removed (ablation)
    v2                 current engine, default settings (table off, title search on)
    v2_with_table      current engine with the legacy table switched back on (ablation)
    v2_no_search       current engine without the title-search tier (ablation)

Positive class = fabricated citation. In the headline ("strict") metrics a citation
counts as flagged when its label is HALLUCINATED (score below the 0.20 threshold) and
UNCERTAIN counts as not flagged. "Review mode" also counts UNCERTAIN as flagged.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from citeverify import AuditConfig, Auditor
from citeverify.clients.http import HttpClient, JsonFileCache, OfflineCacheMiss
from citeverify.metrics import binary_metrics

ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "data" / "benchmark" / "benchmark.csv"
PROBE = ROOT / "data" / "benchmark" / "overlap_probe.csv"
CACHE = ROOT / "data" / "benchmark" / "http_cache.json"
RESULTS_DIR = ROOT / "evaluation" / "results"
REFERENCE_YEAR = 2026  # fixed so results do not change with the calendar
THRESHOLD = 0.20

TIER_ALIASES = {  # v1 tier strings -> v2 tier names, so the tables line up
    "DOI Registry (Crossref)": "DOI registry",
    "DOI Registry (DataCite) + arXiv API": "DOI registry",
    "Temporal Sanity Check": "Temporal check",
    "Known Papers Database": "Known-papers table (legacy)",
    "Plausibility Scoring (Regex Features)": "Plausibility heuristics",
}


@dataclass
class Outcome:
    item: dict
    score: float
    label: str
    tier: str
    error: Optional[str] = None

    @property
    def flagged(self) -> bool:
        return self.score < THRESHOLD


def load(path: Path, split: str) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if split != "all" and path == BENCHMARK:
        rows = [r for r in rows if r["split"] == split]
    for r in rows:
        r["human_label"] = int(r["human_label"])
    return rows


def study_format(text: str) -> str:
    """Lower-case, punctuation-free form used by the original study data
    (e.g. "devlin j chang mw 2019 bert pretraining of deep ...")."""
    t = text.lower().replace("-", "")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ── v1 (legacy) adapter ─────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status: int, data) -> None:
        self.status_code = status
        self._data = data
        self.text = data if isinstance(data, str) else json.dumps(data)

    def json(self):
        return self._data


def _legacy_get(http: HttpClient, misses: list[str]) -> Callable:
    """A stand-in for ``requests.get`` that serves the legacy engine through ``http``.

    The legacy engine swallows exceptions, so cache misses are collected in ``misses``.
    """
    from citeverify.clients.registries import _quote_doi, _slim_crossref_item, _slim_datacite

    def get(url: str, timeout=None, headers=None):  # noqa: ARG001 - signature of requests.get
        try:
            return _route(url)
        except OfflineCacheMiss as exc:
            misses.append(str(exc))
            raise

    def _route(url: str) -> _FakeResponse:
        parts = urlsplit(url)
        if parts.netloc == "api.crossref.org":
            doi = parts.path.split("/works/", 1)[1]
            r = http.get(f"https://api.crossref.org/works/{_quote_doi(doi)}",
                         slim=lambda d: {"message": _slim_crossref_item(d.get("message", {}))})
        elif parts.netloc == "api.datacite.org":
            doi = parts.path.split("/dois/", 1)[1]
            r = http.get(f"https://api.datacite.org/dois/{_quote_doi(doi)}", slim=_slim_datacite)
        elif parts.netloc == "export.arxiv.org":
            arxiv_id = parse_qs(parts.query)["id_list"][0]
            r = http.get("https://export.arxiv.org/api/query",
                         params={"id_list": arxiv_id, "max_results": 1}, as_json=False)
        else:
            raise RuntimeError(f"unexpected legacy request: {url}")
        return _FakeResponse(r.status, r.data)

    return get


@contextmanager
def legacy_engine(http: HttpClient, with_table: bool, misses: list[str]) -> Iterator[Callable]:
    from evaluation.baselines import legacy_auditor as v1

    patches = [mock.patch.object(v1.requests, "get", _legacy_get(http, misses))]
    if not with_table:
        patches.append(mock.patch.object(v1, "lookup_override", lambda text: None))
    for p in patches:
        p.start()
    try:
        yield v1.audit_citation
    finally:
        for p in patches:
            p.stop()


# ── running ─────────────────────────────────────────────────────────────────

def run_v1(rows: list[dict], http: HttpClient, with_table: bool, fmt: Callable[[str], str]) -> list[Outcome]:
    out: list[Outcome] = []
    misses: list[str] = []
    with legacy_engine(http, with_table, misses) as audit:
        for r in rows:
            res = audit(fmt(r["citation"]), r["doi"] or None)
            if misses:
                raise SystemExit(f"v1: response missing for {r['id']} ({misses[0]}). Run with --record.")
            out.append(Outcome(r, res.score, res.label, TIER_ALIASES.get(res.tier, res.tier)))
    return out


def run_v2(rows: list[dict], auditor: Auditor, fmt: Callable[[str], str]) -> list[Outcome]:
    out = []
    for r in rows:
        res = auditor.audit(fmt(r["citation"]), r["doi"] or None)
        if res.error:
            raise SystemExit(f"v2 could not get a response for {r['id']}: {res.error}. Run with --record.")
        out.append(Outcome(r, res.score, res.label, res.tier))
    return out


def systems(http: HttpClient) -> dict[str, Callable[[list[dict], Callable[[str], str]], list[Outcome]]]:
    base = Auditor(AuditConfig(current_year=REFERENCE_YEAR, threshold=THRESHOLD), http)
    return {
        "v1": lambda rows, fmt: run_v1(rows, http, True, fmt),
        "v1_no_table": lambda rows, fmt: run_v1(rows, http, False, fmt),
        "v2": lambda rows, fmt: run_v2(rows, base, fmt),
        "v2_with_table": lambda rows, fmt: run_v2(rows, base.with_config(use_known_papers=True), fmt),
        "v2_no_search": lambda rows, fmt: run_v2(rows, base.with_config(use_search=False), fmt),
    }


# ── metrics ─────────────────────────────────────────────────────────────────

def metrics(outcomes: list[Outcome], review: bool = False) -> dict:
    """Strict mode flags HALLUCINATED only; review mode also flags UNCERTAIN."""
    pred = [int(o.label != "VERIFIED") if review else int(o.flagged) for o in outcomes]
    return binary_metrics([o.item["human_label"] for o in outcomes], pred)


def summarise(outcomes: list[Outcome]) -> dict:
    by_tier: dict[str, list[Outcome]] = defaultdict(list)
    by_cat: dict[str, list[Outcome]] = defaultdict(list)
    for o in outcomes:
        by_tier[o.tier].append(o)
        by_cat[o.item["category"]].append(o)
    three_way = {
        cls: dict(Counter(o.label for o in outcomes if o.item["human_label"] == lab))
        for cls, lab in (("real", 0), ("fabricated", 1))
    }
    return {
        "overall": metrics(outcomes),
        "review_mode": metrics(outcomes, review=True),
        "labels": three_way,
        "by_tier": {
            t: {"n": len(v), "real": sum(o.item["human_label"] == 0 for o in v),
                "fabricated": sum(o.item["human_label"] == 1 for o in v),
                "correct": sum(o.flagged == bool(o.item["human_label"]) for o in v)}
            for t, v in sorted(by_tier.items())
        },
        "by_category": {
            c: {"n": len(v), "label": v[0].item["human_label"],
                "flagged": sum(o.flagged for o in v),
                "correct": sum(o.flagged == bool(o.item["human_label"]) for o in v)}
            for c, v in sorted(by_cat.items())
        },
        "errors": [
            {"id": o.item["id"], "category": o.item["category"], "label": o.item["human_label"],
             "pred_score": o.score, "tier": o.tier}
            for o in outcomes if o.flagged != bool(o.item["human_label"])
        ],
    }


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def render_markdown(report: dict) -> str:
    lines = [f"### Benchmark split: `{report['split']}` ({report['n_items']} citations: "
             f"{report['n_real']} real, {report['n_fabricated']} fabricated)", "",
             "| System | Accuracy | Precision | Recall | F1 | FPR | TP | FP | FN | TN |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, s in report["systems"].items():
        m = s["overall"]
        c = m["confusion"]
        lines.append(f"| {name} | {pct(m['accuracy'])} | {pct(m['precision'])} | {pct(m['recall'])} | "
                     f"{pct(m['f1'])} | {pct(m['false_positive_rate'])} | {c['tp']} | {c['fp']} | {c['fn']} | {c['tn']} |")
    lines += ["", "Review mode (UNCERTAIN also counts as flagged, i.e. \"needs a human look\"):", "",
              "| System | Recall | FPR | Precision | F1 |", "|---|---|---|---|---|"]
    for name, s in report["systems"].items():
        m = s["review_mode"]
        lines.append(f"| {name} | {pct(m['recall'])} | {pct(m['false_positive_rate'])} | "
                     f"{pct(m['precision'])} | {pct(m['f1'])} |")
    lines += ["", "Per detection tier (`v2`):", "", "| Tier | n | real | fabricated | correct |", "|---|---|---|---|---|"]
    for t, v in report["systems"]["v2"]["by_tier"].items():
        lines.append(f"| {t} | {v['n']} | {v['real']} | {v['fabricated']} | {v['correct']} ({pct(v['correct'] / v['n'])}) |")
    lines += ["", "Per category (correct / n):", "",
              "| Category | label | " + " | ".join(report["systems"]) + " |",
              "|---|---|" + "---|" * len(report["systems"])]
    cats = report["systems"]["v2"]["by_category"]
    for c, v in cats.items():
        cells = []
        for s in report["systems"].values():
            cv = s["by_category"][c]
            cells.append(f"{cv['correct']}/{cv['n']}")
        lines.append(f"| {c} | {'fake' if v['label'] else 'real'} | " + " | ".join(cells) + " |")
    if "probe" in report:
        lines += ["", f"### Overlap probe ({report['probe']['n']} correct citations of real papers whose "
                  "first authors are in the legacy known-papers table)", "",
                  "Share wrongly flagged as hallucinated:", "",
                  "| System | as written | study format (lower-case, no punctuation) |", "|---|---|---|"]
        for name, v in report["probe"]["flagged"].items():
            lines.append(f"| {name} | {v['raw']}/{report['probe']['n']} | {v['study']}/{report['probe']['n']} |")
    return "\n".join(lines) + "\n"


def evaluate(split: str, record: bool, cache_path: Path = CACHE, prune: bool = False) -> dict:
    cache = JsonFileCache(cache_path)
    http = HttpClient(cache=cache, offline=not record, timeout=20, retries=3, backoff=2.0)
    rows = load(BENCHMARK, split)
    probe = load(PROBE, "all")
    report: dict = {
        "split": split, "n_items": len(rows),
        "n_real": sum(r["human_label"] == 0 for r in rows),
        "n_fabricated": sum(r["human_label"] == 1 for r in rows),
        "threshold": THRESHOLD, "reference_year": REFERENCE_YEAR, "systems": {},
        "probe": {"n": len(probe), "flagged": {}},
    }
    try:
        for name, run in systems(http).items():
            print(f"  running {name} ...", file=sys.stderr)
            report["systems"][name] = summarise(run(rows, lambda t: t))
            flagged = {}
            for fmt_name, fmt in (("raw", lambda t: t), ("study", study_format)):
                flagged[fmt_name] = sum(o.flagged for o in run(probe, fmt))
            report["probe"]["flagged"][name] = flagged
    finally:
        if prune:
            print(f"  pruned {cache.prune()} unused responses", file=sys.stderr)
        if (record or prune) and cache.dirty:
            cache.save()
            print(f"  cache saved: {len(cache)} responses -> {cache_path}", file=sys.stderr)
    return report


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--record", action="store_true", help="query live APIs and update the cache")
    ap.add_argument("--cache", type=Path, default=CACHE)
    ap.add_argument("--no-save", action="store_true", help="do not write evaluation/results/")
    ap.add_argument("--prune", action="store_true",
                    help="drop cached responses this run did not use (use with --split all)")
    args = ap.parse_args(argv)

    if args.prune and args.split != "all":
        ap.error("--prune needs --split all, or it would drop the other split's responses")
    report = evaluate(args.split, args.record, args.cache, args.prune)
    md = render_markdown(report)
    print(md)
    if not args.no_save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        (RESULTS_DIR / f"{args.split}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        (RESULTS_DIR / f"{args.split}.md").write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
