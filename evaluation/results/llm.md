### Citations written by language models (605: 600 real, 5 fabricated)

Real citations wrongly flagged (false positives), and fabricated ones caught:

| System | Real flagged HALLUCINATED | Real left UNCERTAIN | Fabricated caught (strict) | Fabricated caught (review) |
|---|---|---|---|---|
| v1 | 110/600 (18.3%) | 25 (4.2%) | 5/5 | 5/5 |
| v1_no_table | 110/600 (18.3%) | 25 (4.2%) | 5/5 | 5/5 |
| v2 | 1/600 (0.2%) | 7 (1.2%) | 5/5 | 5/5 |
| v2_no_search | 1/600 (0.2%) | 28 (4.7%) | 5/5 | 5/5 |

Per model (`v2`): real wrongly flagged / real, fabricated caught / fabricated

| Source | Real wrongly flagged | Fabricated caught |
|---|---|---|
| claude-haiku | 1/157 | 3/3 |
| claude-haiku-niche | 0/25 | 0/0 |
| claude-opus | 0/160 | 0/0 |
| claude-opus-niche | 0/53 | 0/0 |
| claude-sonnet | 0/160 | 0/0 |
| claude-sonnet-niche | 0/45 | 2/2 |

Every `v2` error:

| id | truth | category | score | tier |
|---|---|---|---|---|
| claude-haiku-054 | real | real_with_id | 0.05 | DOI registry |
