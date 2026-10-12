"""The benchmark is held out from the legacy table, reproducible, and the published
numbers are exactly what the evaluation script produces from the recorded cache."""
import csv
import json
from pathlib import Path

import pytest

from citeverify.detectors import known_papers
from citeverify.metrics import binary_metrics
from citeverify.parsing import extract_core_citation
from evaluation import build_benchmark
from evaluation.run import BENCHMARK, PROBE, RESULTS_DIR, evaluate, study_format

ROOT = Path(__file__).resolve().parent.parent


def rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_benchmark_does_not_overlap_the_known_papers_table():
    for r in rows(BENCHMARK):
        for text in (r["citation"], study_format(r["citation"])):
            assert known_papers.lookup(extract_core_citation(text)) is None, r["id"]
    first_authors = {r["source_key"].rstrip("0123456789") for r in rows(BENCHMARK)}
    assert not first_authors & (set(known_papers.KNOWN_REAL) | set(known_papers.KNOWN_FAKE))


def test_probe_is_built_from_table_authors():
    probe = rows(PROBE)
    assert all(r["human_label"] == "0" for r in probe)
    hits = sum(known_papers.lookup(extract_core_citation(study_format(r["citation"]))) is not None for r in probe)
    assert hits >= 20


def test_splits_share_no_source_paper():
    data = rows(BENCHMARK)
    real = {s: {r["source_key"] for r in data if r["split"] == s and r["human_label"] == "0"} for s in ("dev", "test")}
    assert not real["dev"] & real["test"]
    derived = {r["source_key"] for r in data if r["split"] == "test" and r["source_key"] != "fabricated"}
    assert derived <= real["test"]


def test_benchmark_file_is_reproducible_from_the_builder():
    built, probe = build_benchmark.build()
    committed = rows(BENCHMARK)
    assert [r["citation"] for r in built] == [r["citation"] for r in committed]
    assert [str(r["human_label"]) for r in built] == [r["human_label"] for r in committed]
    assert [r["citation"] for r in probe] == [r["citation"] for r in rows(PROBE)]


@pytest.mark.parametrize("split", ["dev", "test"])
def test_published_results_reproduce_offline(split):
    """Replays the recorded registry responses; fails if any request is missing."""
    published = json.loads((RESULTS_DIR / f"{split}.json").read_text(encoding="utf-8"))
    report = evaluate(split, record=False)
    for name, system in report["systems"].items():
        assert system["overall"] == published["systems"][name]["overall"], name
        assert system["review_mode"] == published["systems"][name]["review_mode"], name
    assert report["probe"] == published["probe"]


def test_binary_metrics():
    m = binary_metrics([1, 1, 0, 0, 1], [1, 0, 0, 1, 1])
    assert m["confusion"] == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}
    assert m["precision"] == pytest.approx(2 / 3) and m["recall"] == pytest.approx(2 / 3)
    assert m["accuracy"] == pytest.approx(0.6) and m["false_positive_rate"] == pytest.approx(0.5)
    assert binary_metrics([], [])["accuracy"] == 0.0
    with pytest.raises(ValueError):
        binary_metrics([1], [])


def test_llm_citation_labels_reproduce_from_the_label_cache():
    """Labels are rebuilt offline from recorded OpenAlex / doi.org / arXiv responses."""
    from evaluation import label_llm_citations as L
    built, review = L.build(record=False)
    committed = rows(L.OUT)
    assert not review
    assert [(r["id"], str(r["human_label"]), r["category"]) for r in built] == \
           [(r["id"], r["human_label"], r["category"]) for r in committed]


def test_llm_citation_results_reproduce_offline():
    from evaluation import run_llm
    published = json.loads((RESULTS_DIR / "llm.json").read_text(encoding="utf-8"))
    report = run_llm.evaluate(record=False)
    for name, system in report["systems"].items():
        assert system["overall"] == published["systems"][name]["overall"], name
        assert system["labels"] == published["systems"][name]["labels"], name
