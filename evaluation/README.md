# Evaluation

Everything on this page is produced by code in this directory and can be re-run
offline in a few seconds:

```bash
python -m evaluation.run --split test   # writes evaluation/results/test.{json,md}
python -m evaluation.run --split dev
```

`tests/test_evaluation.py` re-runs both splits from the recorded responses and fails if
the numbers differ from the committed `results/*.json`.

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
real papers whose first authors are in the first version's hard-coded "known papers"
lookup table (Vaswani 2017, Devlin 2019, Hochreiter 1997, ...). It is not part of the
benchmark; it shows what a fixed lookup table does on papers it lists.

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
contributes no detection ability on unseen papers. On the overlap probe it does harm,
because a list keyed by author, year and a title word cannot tell a correct citation of a
listed paper from a fabricated one. This is why v2 verifies against registries instead;
the table is off by default and kept only for this ablation.

| System | correct citations flagged as fake (as written) | (lower-case, no punctuation) |
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

## Citations written by language models

**Collection.**
- *ChatGPT and Gemini* (held out): the general reading-list prompt
  ([`prompt_general.txt`](../data/llm_citations/prompt_general.txt)) in each web app with
  browsing off, on 2026-10-12. ChatGPT gave 160 references; Gemini chose to give 2 per
  topic (40). Transcribed as given; a DOI the model told the reader to verify is left empty.
- *Claude Haiku, Sonnet and Opus*: the same prompt (480 references) and narrow, recent-work
  requests for 15 topics ([`prompt_niche.txt`](../data/llm_citations/prompt_niche.txt), 125
  references; the models gave fewer than asked rather than invent), as subagents with all
  lookup tools disabled. The prompts do not mention evaluation.

Raw outputs are in [`data/llm_citations/raw/`](../data/llm_citations/raw).

**Labelling** ([`label_llm_citations.py`](label_llm_citations.py)). Ground truth comes
from OpenAlex, which CiteVerify does not use, with doi.org for DOI existence and the arXiv
API for arXiv IDs. A citation is real when a work exists with a matching title (or the
same main title when the registry drops the subtitle), the cited first author among its
authors (when the record lists any), and a year within two of the cited one; a given DOI
or arXiv ID must point to that work. Venue and pages are not checked. Everything else is
fabricated. Every item the labeller called fabricated was checked by hand; that found
bugs in the labeller (title parsing, hyphenated names, online-first years, quotes), fixed
by changing its rules, never by editing labels. Six items are decided by hand, with
sources, in [`manual_labels.csv`](../data/llm_citations/manual_labels.csv). Each batch's
labels were committed before CiteVerify was run on it.

Result: 782 real, 23 fabricated. All 23 fabrications are identifiers: 18 DOIs or arXiv
IDs that resolve to a different paper and 5 DOIs that do not exist.

**Versions and what is held out.**

| Version | Changed after seeing | Held out on |
|---|---|---|
| v2 | benchmark dev split | benchmark test split, Claude set |
| v2.1 | Claude set errors | ChatGPT + Gemini |
| v2.2 | ChatGPT + Gemini errors | nothing new |

**Held-out results on ChatGPT + Gemini** (200: 182 real, 18 fabricated;
[`results/llm_heldout_v2.1.md`](results/llm_heldout_v2.1.md)):

| System | Precision | Recall | F1 | Real flagged | Review mode: caught / real sent for review |
|---|---|---|---|---|---|
| v1 | 37.5% | 18/18 | 54.5% | 30/182 | 18/18 / 40 |
| v2.1 | 85.0% | 17/18 | 89.5% | 3/182 | 18/18 / 5 |

**Held-out results on the Claude set** (605: 600 real, 5 fabricated;
[`results/llm_frozen.md`](results/llm_frozen.md)): v1 wrongly flags 110 of 600, v2 flags 4
and catches 4 of 5.

**Current version on all 805** ([`results/llm.md`](results/llm.md)): v2.2 wrongly flags 2
of 782 and catches 22 of 23 (23 of 23 in review mode); v1 wrongly flags 140 of 782.

**Every error, and what was done about it:**

| Citation | Version | Result | Cause | Fix |
|---|---|---|---|---|
| Cao et al. (2023), arXiv ID of a different paper | v2 | missed (UNCERTAIN) | an arXiv ID in the DOI field was discarded as "not a DOI" | v2.1: arXiv IDs in the DOI field (new and old style) are resolved |
| Gottesman (1997), `quant-ph/9705052` | v2 | false alarm | same, plus "[Doctoral dissertation]" read as part of the title | v2.1: same; bracketed notes dropped from titles |
| Chetty et al. (2014), "Active vs. passive decisions ..." (×2) | v2 | false alarm | title cut at "vs." | v2.1: "vs.", "e.g.", "i.e." and "U.S." don't end a title |
| 43 citations of arXiv papers by their venue year | v2 | UNCERTAIN once arXiv IDs were resolved | a later year than the preprint counted as a mismatch | v2.1: up to 3 years after an arXiv preprint matches |
| Graham et al. (2021), ... COVID-19 "long haulers" | v2.1 | false alarm | a quoted phrase in an APA title was read as an IEEE quoted title | v2.2: APA layout wins when the year comes first |
| Tandoc et al. (2018), Defining "fake news" ... | v2.1 | false alarm | same | v2.2: same |
| Tapu et al. (2018), Pattern Recognition Letters 137 (Claude Haiku and ChatGPT) | all | false alarm | volume 137 is 2020; 2018 is the online-first year | not changed: flagging this is defensible |
| Ji et al. (2023), "Towards mitigating LLM hallucination via self reflection" | all | UNCERTAIN | real paper and correct arXiv ID, paraphrased title (labelled fabricated by the title rule) | not changed: sent for review, which is the right outcome |

None of these fixes changes the benchmark test split; v2.1 additionally verifies one more
real dev citation (SciPy 1.0).

## Limitations

- The language-model set has 23 fabrications, so recall is measured coarsely (one item is
  about 5 points on the held-out 18). Model versions of the ChatGPT and Gemini web apps
  were not recorded, and each answered one prompt once.
- The fabricated class is synthetic. Real hallucinations from language models can be
  subtler (plausible titles, real co-author groups) and this benchmark does not measure
  that distribution.
- Citations are rendered from templates in three styles; messy real-world strings
  (OCR, truncated, mixed styles) are harder to parse.
- 270 citations is small: one item moves test accuracy by about 0.7 points.
- The registry tiers depend on Crossref/DataCite/arXiv coverage and metadata quality.
  Books, theses and reports that are not indexed fall back to "no matching record".
