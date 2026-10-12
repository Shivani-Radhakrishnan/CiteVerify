### Learned risk model (logreg C=0.3, trained on 739 citations, 61 fabricated)

Flag threshold chosen on out-of-fold training scores: risk >= 0.305.

Model selection (5-fold out-of-fold, training data only):

| Candidate | log-loss | average precision |
|---|---|---|
| logreg C=0.03 | 0.0439 | 0.9841 |
| logreg C=0.1 | 0.0302 | 0.9861 |
| logreg C=0.3 (selected) | 0.0254 | 0.9872 |
| logreg C=1.0 | 0.0255 | 0.9864 |
| logreg C=3.0 | 0.0280 | 0.9857 |
| gradient boosting | 0.0256 | 0.9469 |

**Test: benchmark test** (136 citations, 56 fabricated)

| | ROC-AUC | Avg. precision | Brier | ECE | Precision | Recall | F1 | Real flagged |
|---|---|---|---|---|---|---|---|---|
| rules (v2.2), HALLUCINATED only | 0.986 | 0.987 | 0.025 | 0.073 | 100.0% | 47/56 | 91.3% | 0/80 |
| learned risk | 0.999 | 0.999 | 0.019 | 0.031 | 98.2% | 54/56 | 97.3% | 1/80 |
| rules, review mode (UNCERTAIN counts as flagged) | | | | | 96.5% | 55/56 | 97.3% | 2/80 (10 sent for review) |

**Test: ChatGPT + Gemini** (200 citations, 18 fabricated)

| | ROC-AUC | Avg. precision | Brier | ECE | Precision | Recall | F1 | Real flagged |
|---|---|---|---|---|---|---|---|---|
| rules (v2.2), HALLUCINATED only | 0.999 | 0.990 | 0.011 | 0.036 | 94.4% | 17/18 | 94.4% | 1/182 |
| learned risk | 0.999 | 0.992 | 0.006 | 0.011 | 100.0% | 17/18 | 97.1% | 0/182 |
| rules, review mode (UNCERTAIN counts as flagged) | | | | | 81.8% | 18/18 | 90.0% | 4/182 (4 sent for review) |

**Test: all test** (336 citations, 74 fabricated)

| | ROC-AUC | Avg. precision | Brier | ECE | Precision | Recall | F1 | Real flagged |
|---|---|---|---|---|---|---|---|---|
| rules (v2.2), HALLUCINATED only | 0.990 | 0.982 | 0.017 | 0.043 | 98.5% | 64/74 | 92.1% | 1/262 |
| learned risk | 0.999 | 0.998 | 0.011 | 0.017 | 98.6% | 71/74 | 97.3% | 1/262 |
| rules, review mode (UNCERTAIN counts as flagged) | | | | | 92.4% | 73/74 | 95.4% | 6/262 (14 sent for review) |

Largest weights (standardised features; positive = more likely fabricated):

| Feature | Weight |
|---|---|
| `rule_score` | -1.47 |
| `author_agree` | -0.98 |
| `year_gap` | +0.52 |
| `title_sim` | -0.44 |
| `author_unchecked` | -0.43 |
| `year_agree` | -0.37 |
| `style_ieee` | +0.35 |
| `tier_heuristic` | -0.33 |
| `style_apa` | -0.25 |
| `n_authors` | -0.22 |
