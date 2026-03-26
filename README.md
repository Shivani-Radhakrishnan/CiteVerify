# 🔬 CiteVerify — Citation Hallucination Detection Platform

Convert your Colab citation audit research into a production Streamlit app.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Features

### 🔍 Single Citation Audit
Paste any citation text (with or without a DOI) and get an instant verdict:
- Plausibility score (0–1)
- Detection tier used
- Explanation of signals detected
- Recommended action

### 📂 Batch Audit
- Upload a CSV with a `citation` column (and optional `doi` column)
- Paste multiple citations directly
- Download results as CSV
- Performance metrics if you include a `human_label` column (0=real, 1=fake)

### 📊 System Stats
- Benchmark results from the training study
- Feature signal effectiveness table
- Confusion matrix
- Root cause analysis of remaining errors

### ❓ How It Works
Full explanation of the 4-tier detection pipeline.

## Detection Pipeline

```
Citation text
    │
    ▼
Tier 1: DOI provided?  ──yes──► CrossRef API lookup ──► verdict
    │ no
    ▼
Tier 2: Temporal check ──fail──► HALLUCINATION (future year)
    │ pass
    ▼
Tier 3: Known papers DB ──match──► score override (real/fake)
    │ no match
    ▼
Tier 4: Plausibility scoring (regex features) ──► score → verdict
```

## CSV Format for Batch Upload

```csv
citation,doi,human_label
"vaswani a shazeer n 2017 attention is all you need neurips",,0
"lewis p 2020 retrieval augmented generation",10.18653/v1/2020.acl-main.447,0
"ji z 2023 survey of hallucination in large language models",,1
```

## Adjusting the Threshold

Use the sidebar slider to change the plausibility threshold (default: 0.20).
- Higher threshold = more conservative (flags more as hallucinations)
- Lower threshold = more permissive (flags fewer as hallucinations)

The optimal threshold from the training study was 0.20, giving 97.6% accuracy on 212 labeled citations.

## Project Structure

```
citeverify/
├── app.py              # Streamlit UI
├── requirements.txt    # Dependencies
├── README.md           # This file
└── utils/
    ├── __init__.py
    └── auditor.py      # Core detection engine
```
