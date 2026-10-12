### Citations written by language models (805: 782 real, 23 fabricated)

Real citations wrongly flagged (false positives), and fabricated ones caught:

| System | Real flagged HALLUCINATED | Real left UNCERTAIN | Fabricated caught (strict) | Fabricated caught (review) |
|---|---|---|---|---|
| v1 | 140/782 (17.9%) | 35 (4.5%) | 23/23 | 23/23 |
| v1_no_table | 140/782 (17.9%) | 35 (4.5%) | 23/23 | 23/23 |
| v2 | 4/782 (0.5%) | 9 (1.2%) | 22/23 | 23/23 |
| v2_no_search | 3/782 (0.4%) | 39 (5.0%) | 22/23 | 23/23 |

Per model (`v2`): real wrongly flagged / real, fabricated caught / fabricated

| Source | Real wrongly flagged | Fabricated caught |
|---|---|---|
| chatgpt | 3/147 | 12/13 |
| claude-haiku | 1/157 | 3/3 |
| claude-haiku-niche | 0/25 | 0/0 |
| claude-opus | 0/160 | 0/0 |
| claude-opus-niche | 0/53 | 0/0 |
| claude-sonnet | 0/160 | 0/0 |
| claude-sonnet-niche | 0/45 | 2/2 |
| gemini | 0/35 | 5/5 |

Every `v2` error:

| id | truth | category | score | tier |
|---|---|---|---|---|
| chatgpt-055 | real | real_text_only | 0.10 | Registry search |
| chatgpt-085 | fabricated | doi_mismatch | 0.50 | DOI registry |
| chatgpt-109 | real | real_with_id | 0.05 | DOI registry |
| chatgpt-150 | real | real_with_id | 0.05 | DOI registry |
| claude-haiku-054 | real | real_with_id | 0.05 | DOI registry |
