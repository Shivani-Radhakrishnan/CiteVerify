# Evaluation

Everything on this page is produced by code in this directory and can be re-run
offline in a few seconds:

```bash
python -m evaluation.run --split test   # writes evaluation/results/test.{json,md}
python -m evaluation.run --split dev
```

`tests/test_evaluation.py` re-runs both splits from the recorded responses and fails if
the numbers differ from the committed `results/*.json`.

## Why the old number was replaced

Earlier versions of the README said the engine reached "97.6% accuracy on 212 labeled
citations". That number cannot be reproduced and should not be compared with the
numbers below:

- **The 212 labelled citations are not in this repository** (nor in its git history),
  so the figure cannot be re-run.
- **The figure partly measured memorisation.** The engine contained a hard-coded
  "known papers" table (`KNOWN_REAL` / `KNOWN_FAKE`, now in
  `citeverify/detectors/known_papers.py`) keyed by first-author surname, year and a
  title keyword. The in-app documentation described it as "known-real and known-fake
  citations from the study set", i.e. it was built from the same data the accuracy was
  measured on. Several entries (`harwood` 2023 "bibliographic", `okafor` 2023
  "bibliometric", `larsen` 2023 "synthetic doi", `owens` 2022 "venue scoring") do not
  point to well-known papers and appear to be items from that study set.
- **The table labels real papers as fake.** `KNOWN_FAKE` includes BERT, scikit-learn,
  RAG, FEVER, DPR, Sentence-BERT, ROUGE, GPT-2, InstructGPT and others. It cannot tell a
  correct citation of these papers from a fabricated one, so correct citations of them
  are flagged as hallucinated (see the overlap probe below).
- **The plausibility features learned the study's format, not fabrication.** They reward
  inline fragments ("Smith et al. 2020 and") and penalise full reference entries
  (surname + initials, title after the year, ending in a venue). On a list of correctly
  formatted references that association does not hold: the v1 engine leaves almost
  every text-only reference as UNCERTAIN, real or fake.

The table is now off by default and kept only for the ablation. The heuristics are only
used as a last-resort fallback when a citation cannot be looked up.

## The benchmark

`data/benchmark/benchmark.csv` (270 citations) is generated deterministically by
`python -m evaluation.build_benchmark` from two hand-curated source files.

**Real class (label 0): 158 citations of 79 real papers.**
`sources/real_papers.csv` lists 79 widely cited papers from machine learning, NLP,
vision, statistics, biology, physics and the social sciences, with authors, year,
title, venue and DOI. Every DOI was resolved against Crossref (or DataCite for arXiv
DOIs) and the returned title, year and first author were checked by hand before the
file was frozen. No paper has a first author that appears in the legacy table, and a
test asserts the table matches none of the 270 citations. Each paper is rendered once
with its DOI and once without, in a randomly chosen style (APA, IEEE or Vancouver).
Registry metadata is used as-is, including its quirks (Crossref dates BLEU to 2001; the
conventional citation year is 2002; one record has no date).

**Fabricated class (label 1): 112 synthetic citations.** These are generated, not
collected from a language model, and every one is fabricated by construction:

| Category | Per split | How it is made |
|---|---|---|
| `fabricated_doi` | 8 | invented authors and title + a DOI in a number range the publisher has not issued (all confirmed unregistered) |
| `fabricated_arxiv` | 3 | invented paper + an arXiv DOI that does not exist |
| `doi_swap` | 6 | a real citation paired with another paper's DOI |
| `wrong_year_doi` | 6 | a real citation with the year shifted by 2-6 years, real DOI |
| `wrong_author_doi` | 5 | a real citation with the first author replaced, real DOI |
| `future_year_doi` | 3 | a real citation dated 2029-2040, real DOI |
| `fabricated_text` | 10 | invented authors, title and (real) venue, no DOI |
| `chimeric_text` | 6 | real authors, year and venue with an invented title, no DOI |
| `misattributed_text` | 5 | a real title credited to another paper's authors and year, no DOI |
| `future_year_text` | 4 | invented citation dated 2029-2040, no DOI |

**Splits.** Papers are split 50/50 into `dev` and `test` before anything is generated,
so a paper and every perturbation of it are in one split only. All detection changes in
v2 were developed by looking at errors on `dev`. The `test` responses were recorded and
scored once, after the code was frozen; nothing was changed after seeing them.

**Overlap probe.** `data/benchmark/overlap_probe.csv` holds 25 *correct* citations of
real papers whose first authors are in the legacy table (Vaswani 2017, Devlin 2019,
Hochreiter 1997, ...). It is not part of the benchmark; it shows what the table does.

**Recorded responses.** `data/benchmark/http_cache.json` holds every Crossref,
DataCite, arXiv and doi.org response the systems need (trimmed to the fields used).
`python -m evaluation.run --record --split <split>` re-queries the live APIs and
updates it; registry contents change over time, so a re-recording can shift results.

## Results (test split, 136 citations: 80 real, 56 fabricated)

Positive class = fabricated. "Strict" counts only HALLUCINATED as a detection;
"review mode" also counts UNCERTAIN ("check by hand") as a detection.

| System | Accuracy | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|
| v1 (original engine, as shipped) | 81.6% | 97.0% | 57.1% | 71.9% | 1.2% |
| v1 without the known-papers table | 81.6% | 97.0% | 57.1% | 71.9% | 1.2% |
| **v2 (current engine)** | **93.4%** | **100.0%** | **83.9%** | **91.3%** | **0.0%** |
| v2 with the known-papers table | 93.4% | 100.0% | 83.9% | 91.3% | 0.0% |
| v2 without title search | 83.8% | 100.0% | 60.7% | 75.6% | 0.0% |

Confusion matrix, v2 strict (TP = fabricated and flagged): TP 47, FP 0, FN 9, TN 80.

Review mode: v2 recall 98.2% at a 2.5% false-positive rate (2 of 80 real citations
sent for review); v1 recall 94.6% at a 51.2% false-positive rate (it leaves 40 of 80
real citations UNCERTAIN).

Per detection tier, v2: DOI registry 67/68 correct, registry search 53/61, temporal
check 7/7. The full per-category breakdown is in [`results/test.md`](results/test.md);
dev-split numbers are in [`results/dev.md`](results/dev.md).

**Ablation of the known-papers table.** On the held-out benchmark the table changes
nothing (identical rows above): by construction no benchmark citation matches it, so it
contributes no detection ability on unseen papers. On the overlap probe it does harm:

| System | correct citations flagged as fake (as written) | (study format: lower-case, no punctuation) |
|---|---|---|
| v1 (table on) | 7 / 25 | 16 / 25 |
| v1, table removed | 0 / 25 | 3 / 25 |
| v2 (table off) | 0 / 25 | 2 / 25 |
| v2, table on | 7 / 25 | 16 / 25 |

**Where v2 still misses (test):** 7 fabricated text-only citations whose titles are
close to, but not the same as, a real record land in the "partial match" band
(UNCERTAIN, not flagged); 1 misattributed citation with a short, generic title is left
UNCERTAIN by design; 1 wrong-year citation passes because its Crossref record has no
date.

## Limitations

- The fabricated class is synthetic. Real hallucinations from language models can be
  subtler (plausible titles, real co-author groups) and this benchmark does not measure
  that distribution.
- Citations are rendered from templates in three styles; messy real-world strings
  (OCR, truncated, mixed styles) are harder to parse.
- 270 citations is small: one item moves test accuracy by about 0.7 points.
- The registry tiers depend on Crossref/DataCite/arXiv coverage and metadata quality.
  Books, theses and reports that are not indexed fall back to "no matching record".
