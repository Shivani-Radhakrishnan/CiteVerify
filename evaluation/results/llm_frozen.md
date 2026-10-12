### Citations written by language models (605: 600 real, 5 fabricated)

Real citations wrongly flagged (false positives), and fabricated ones caught:

| System | Real flagged HALLUCINATED | Real left UNCERTAIN | Fabricated caught (strict) | Fabricated caught (review) |
|---|---|---|---|---|
| v1 | 110/600 (18.3%) | 25 (4.2%) | 5/5 | 5/5 |
| v1_no_table | 110/600 (18.3%) | 25 (4.2%) | 5/5 | 5/5 |
| v2 | 4/600 (0.7%) | 41 (6.8%) | 4/5 | 5/5 |
| v2_no_search | 3/600 (0.5%) | 134 (22.3%) | 4/5 | 5/5 |

Per model (`v2`): real wrongly flagged / real, fabricated caught / fabricated

| Source | Real wrongly flagged | Fabricated caught |
|---|---|---|
| claude-haiku | 1/157 | 3/3 |
| claude-haiku-niche | 0/25 | 0/0 |
| claude-opus | 1/160 | 0/0 |
| claude-opus-niche | 0/53 | 0/0 |
| claude-sonnet | 2/160 | 0/0 |
| claude-sonnet-niche | 0/45 | 1/2 |

Every `v2` error:

| id | truth | category | score | tier |
|---|---|---|---|---|
| claude-haiku-054 | real | real_with_id | 0.05 | DOI registry |
| claude-opus-044 | real | real_with_id | 0.05 | DOI registry |
| claude-sonnet-niche-027 | fabricated | doi_mismatch | 0.40 | Registry search |
| claude-sonnet-045 | real | real_with_id | 0.05 | DOI registry |
| claude-sonnet-155 | real | real_with_id | 0.15 | Registry search |
