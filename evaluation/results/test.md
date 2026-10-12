### Benchmark split: `test` (136 citations: 80 real, 56 fabricated)

| System | Accuracy | Precision | Recall | F1 | FPR | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|
| v1 | 81.6% | 97.0% | 57.1% | 71.9% | 1.2% | 32 | 1 | 24 | 79 |
| v1_no_table | 81.6% | 97.0% | 57.1% | 71.9% | 1.2% | 32 | 1 | 24 | 79 |
| v2 | 93.4% | 100.0% | 83.9% | 91.3% | 0.0% | 47 | 0 | 9 | 80 |
| v2_with_table | 93.4% | 100.0% | 83.9% | 91.3% | 0.0% | 47 | 0 | 9 | 80 |
| v2_no_search | 83.8% | 100.0% | 60.7% | 75.6% | 0.0% | 34 | 0 | 22 | 80 |

Review mode (UNCERTAIN also counts as flagged, i.e. "needs a human look"):

| System | Recall | FPR | Precision | F1 |
|---|---|---|---|---|
| v1 | 94.6% | 51.2% | 56.4% | 70.7% |
| v1_no_table | 94.6% | 51.2% | 56.4% | 70.7% |
| v2 | 98.2% | 2.5% | 96.5% | 97.3% |
| v2_with_table | 98.2% | 2.5% | 96.5% | 97.3% |
| v2_no_search | 98.2% | 50.0% | 57.9% | 72.8% |

Per detection tier (`v2`):

| Tier | n | real | fabricated | correct |
|---|---|---|---|---|
| DOI registry | 68 | 40 | 28 | 67 (98.5%) |
| Registry search | 61 | 40 | 21 | 53 (86.9%) |
| Temporal check | 7 | 0 | 7 | 7 (100.0%) |

Per category (correct / n):

| Category | label | v1 | v1_no_table | v2 | v2_with_table | v2_no_search |
|---|---|---|---|---|---|---|
| chimeric_text | fake | 0/6 | 0/6 | 2/6 | 2/6 | 0/6 |
| doi_swap | fake | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| fabricated_arxiv | fake | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| fabricated_doi | fake | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| fabricated_text | fake | 0/10 | 0/10 | 7/10 | 7/10 | 0/10 |
| future_year_doi | fake | 1/3 | 1/3 | 3/3 | 3/3 | 3/3 |
| future_year_text | fake | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| misattributed_text | fake | 0/5 | 0/5 | 4/5 | 4/5 | 0/5 |
| real_text_only | real | 40/40 | 40/40 | 40/40 | 40/40 | 40/40 |
| real_with_doi | real | 39/40 | 39/40 | 40/40 | 40/40 | 40/40 |
| wrong_author_doi | fake | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |
| wrong_year_doi | fake | 5/6 | 5/6 | 5/6 | 5/6 | 5/6 |

### Overlap probe (25 correct citations of real papers whose first authors are in the legacy known-papers table)

Share wrongly flagged as hallucinated:

| System | as written | study format (lower-case, no punctuation) |
|---|---|---|
| v1 | 7/25 | 16/25 |
| v1_no_table | 0/25 | 3/25 |
| v2 | 0/25 | 2/25 |
| v2_with_table | 7/25 | 16/25 |
| v2_no_search | 0/25 | 3/25 |
