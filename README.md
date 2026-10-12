# 🔬 CiteVerify — Citation Hallucination Detection

[![tests](https://github.com/Shivani-Radhakrishnan/CiteVerify/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Shivani-Radhakrishnan/CiteVerify/actions/workflows/tests.yml)

CiteVerify checks whether an academic reference is real and correctly cited, the kind of
check you need when a writing tool may have invented its sources. Paste a reference, with
or without a DOI: it rejects impossible dates, resolves the DOI (or searches Crossref and
arXiv by title), and compares the cited title, year and first author with the registry
record. Every verdict comes with the evidence behind it. It is a Streamlit app backed by a
typed Python package, and its accuracy is measured on a held-out benchmark that you can
re-run offline.

![CiteVerify flagging a citation whose DOI is real but whose year is wrong](docs/screenshot.png)

## How it works

```
citation text (+ optional DOI)
        │
        ▼
 1  Temporal check ── year in the future ─────────────────────────► HALLUCINATED
        │ ok
        ▼
 2  DOI given or found in text?
        │ yes: Crossref → DataCite → doi.org   (arXiv DOIs: DataCite → arXiv API)
        │      ├─ DOI not registered anywhere ───────────────────► HALLUCINATED
        │      ├─ title / year / first author contradict record ─► HALLUCINATED
        │      ├─ small discrepancy (year off by one, ...) ──────► UNCERTAIN
        │      └─ all checked fields agree ──────────────────────► VERIFIED
        │ no
        ▼
 3  Title search: Crossref bibliographic query, then arXiv
        │      ├─ same title, consistent year and author ────────► VERIFIED
        │      ├─ same title, credited to other authors/year ────► HALLUCINATED
        │      ├─ only a partial title match ────────────────────► UNCERTAIN
        │      └─ no similar title anywhere ─────────────────────► HALLUCINATED
        │ nothing searchable / registries unreachable
        ▼
 4  Heuristic fallback (surface patterns; never returns VERIFIED)
```

Under the hood: a citation parser for APA, IEEE and Vancouver styles (authors, year,
title, venue, DOI/arXiv ID); accent-, markup- and subtitle-tolerant title matching that
ignores errata and reviews; year checks against every date a registry lists; and an HTTP
layer with timeouts, retries, per-host rate limiting and caching. When a registry is down,
the result says so instead of guessing.

## Results

Evaluated on a held-out test split of **136 citations** (80 correct citations of real
papers with hand-checked DOIs, 56 synthetic fabrications such as non-existent DOIs,
swapped DOIs, wrong years or authors, invented titles and misattributed titles). The
positive class is "fabricated"; a citation counts as detected when it is labelled
HALLUCINATED.

| System | Accuracy | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|
| v1 (original engine) | 81.6% | 97.0% | 57.1% | 71.9% | 1.2% |
| **v2 (this version)** | **93.4%** | **100.0%** | **83.9%** | **91.3%** | **0.0%** |
| v2 without title search (ablation) | 83.8% | 100.0% | 60.7% | 75.6% | 0.0% |

v2 confusion matrix: 47 true positives, 0 false positives, 9 false negatives, 80 true
negatives. Counting UNCERTAIN ("check by hand") as a detection, v2 catches 55 of 56
fabrications while sending 2 of 80 real citations for review. Per tier: DOI registry
67/68 correct, title search 53/61, temporal check 7/7.

Reproduce (offline, a few seconds; registry responses are recorded in the repo):

```bash
python -m evaluation.run --split test
```

**About the earlier "97.6% accuracy" claim.** Earlier versions of this README reported
97.6% accuracy on 212 labelled citations. Those 212 citations are not in the repository,
and the engine contained a hand-built "known papers" table taken from the same study set,
so that figure partly measured memorisation. The table also marks several real papers
(BERT, scikit-learn, GPT-2, ROUGE, ...) as fake. It is now switched off by default; on
the held-out benchmark it changes nothing, and on 25 correct citations of the papers it
lists it wrongly flags 7. The benchmark construction, dev/test protocol, ablations and
per-category results are documented in [`evaluation/README.md`](evaluation/README.md).

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py          # http://localhost:8501
```

From Python:

```python
from citeverify import Auditor

result = Auditor().audit(
    "Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation.",
    doi="10.1162/neco.1997.9.8.1735",
)
print(result.label, result.score, result.tier)   # VERIFIED 0.97 DOI registry
for s in result.signals:
    print(s.status, s.name, s.detail)
```

The app has six pages: single audit, batch audit (CSV or pasted list, parallel lookups,
CSV export, metrics against a `human_label` column), side-by-side compare, study mode
(metrics, confusion matrix and threshold sweep on your own labelled data), analytics
(the benchmark results), and documentation.

Batch CSV format:

```csv
citation,doi,human_label
"Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation.",10.1162/neco.1997.9.8.1735,0
"Kingma DP, Ba J. Adam: A method for stochastic optimization. arXiv preprint. 2014.",,0
"Ivanova, A. (2017). Diffusion priors: Rethinking soil moisture estimation. Neural Networks.",,1
```

## Project structure

```
CiteVerify/
├── app.py                     # Streamlit entry point and page routing
├── config.py                  # design tokens and CSS (presentation only)
├── citeverify/                # detection engine (no Streamlit dependency)
│   ├── pipeline.py            # Auditor / AuditConfig: routes a citation through the tiers
│   ├── parsing.py             # DOI/arXiv/year/author/title extraction
│   ├── matching.py            # title similarity and field checks against a record
│   ├── metrics.py             # accuracy / precision / recall / F1
│   ├── models.py              # AuditResult, WorkRecord, Signal, ...
│   ├── clients/               # HTTP layer + Crossref, DataCite, arXiv, doi.org clients
│   └── detectors/             # temporal, doi, search, heuristics, known_papers (legacy)
├── pages/                     # Streamlit pages
├── utils/                     # UI helpers, field highlighting, PDF report
├── evaluation/                # benchmark builder, evaluation script, results, v1 baseline
├── data/benchmark/            # benchmark CSVs, source paper lists, recorded API responses
└── tests/                     # pytest suite (network fully mocked)
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

126 tests cover DOI and citation parsing, title/year/author matching, the HTTP layer
(retries, backoff, caching, offline mode), every registry client, tier routing and
verdicts of the full pipeline, the UI helpers, and the benchmark itself (no overlap with
the legacy table, splits share no paper, published numbers reproduce from the recorded
responses). GitHub Actions runs them on Python 3.10–3.12.

## Limitations

- Only as complete as Crossref, DataCite and arXiv: unindexed books, theses and reports
  can come back as "no matching record".
- Fabricated titles that closely resemble a real title land in UNCERTAIN rather than
  being flagged (7 of the 9 test misses).
- The fabricated half of the benchmark is synthetic and the citations are rendered in
  three styles; real model hallucinations and messy real-world strings can be harder.
- The benchmark is small (270 citations); one test item is worth about 0.7 points of
  accuracy.
