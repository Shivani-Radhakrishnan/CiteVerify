### Benchmark split: `dev` (134 citations: 78 real, 56 fabricated)

| System | Accuracy | Precision | Recall | F1 | FPR | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|
| v1 | 79.9% | 96.8% | 53.6% | 69.0% | 1.3% | 30 | 1 | 26 | 77 |
| v1_no_table | 79.9% | 96.8% | 53.6% | 69.0% | 1.3% | 30 | 1 | 26 | 77 |
| v2 | 97.0% | 100.0% | 92.9% | 96.3% | 0.0% | 52 | 0 | 4 | 78 |
| v2_with_table | 97.0% | 100.0% | 92.9% | 96.3% | 0.0% | 52 | 0 | 4 | 78 |
| v2_no_search | 84.3% | 100.0% | 62.5% | 76.9% | 0.0% | 35 | 0 | 21 | 78 |

Review mode (UNCERTAIN also counts as flagged, i.e. "needs a human look"):

| System | Recall | FPR | Precision | F1 |
|---|---|---|---|---|
| v1 | 91.1% | 51.3% | 56.0% | 69.4% |
| v1_no_table | 91.1% | 51.3% | 56.0% | 69.4% |
| v2 | 100.0% | 5.1% | 93.3% | 96.6% |
| v2_with_table | 100.0% | 5.1% | 93.3% | 96.6% |
| v2_no_search | 100.0% | 51.3% | 58.3% | 73.7% |

Per detection tier (`v2`):

| Tier | n | real | fabricated | correct |
|---|---|---|---|---|
| DOI registry | 67 | 39 | 28 | 67 (100.0%) |
| Plausibility heuristics | 1 | 1 | 0 | 1 (100.0%) |
| Registry search | 59 | 38 | 21 | 55 (93.2%) |
| Temporal check | 7 | 0 | 7 | 7 (100.0%) |

Per category (correct / n):

| Category | label | v1 | v1_no_table | v2 | v2_with_table | v2_no_search |
|---|---|---|---|---|---|---|
| chimeric_text | fake | 0/6 | 0/6 | 6/6 | 6/6 | 0/6 |
| doi_swap | fake | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| fabricated_arxiv | fake | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| fabricated_doi | fake | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 |
| fabricated_text | fake | 0/10 | 0/10 | 6/10 | 6/10 | 0/10 |
| future_year_doi | fake | 0/3 | 0/3 | 3/3 | 3/3 | 3/3 |
| future_year_text | fake | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| misattributed_text | fake | 0/5 | 0/5 | 5/5 | 5/5 | 0/5 |
| real_text_only | real | 39/39 | 39/39 | 39/39 | 39/39 | 39/39 |
| real_with_doi | real | 38/39 | 38/39 | 39/39 | 39/39 | 39/39 |
| wrong_author_doi | fake | 3/5 | 3/5 | 5/5 | 5/5 | 5/5 |
| wrong_year_doi | fake | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |

### Overlap probe (25 correct citations of real papers whose first authors are in the legacy known-papers table)

Share wrongly flagged as hallucinated:

| System | as written | study format (lower-case, no punctuation) |
|---|---|---|
| v1 | 7/25 | 16/25 |
| v1_no_table | 0/25 | 3/25 |
| v2 | 0/25 | 2/25 |
| v2_with_table | 7/25 | 16/25 |
| v2_no_search | 0/25 | 3/25 |
