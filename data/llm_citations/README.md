# Citations written by language models

| File | What it is |
|---|---|
| `raw/claude-{haiku,sonnet,opus}.jsonl` | Answers to `prompt_general.txt`, collected through Claude subagents with all lookup tools disabled |
| `raw/claude-*-niche.jsonl` | Answers to `prompt_niche.txt`, same setup |
| `raw/chatgpt.jsonl`, `raw/gemini.jsonl` | Answers to `prompt_general.txt` in the ChatGPT and Gemini web apps with browsing off, collected on 2026-10-12 (model versions not recorded by the apps). Transcribed as given; a DOI the model itself said to verify, or left out, is an empty `doi`. Gemini chose to give 2 references per topic instead of 8. |
| `llm_citations.csv` | Labels produced by `python -m evaluation.label_llm_citations` |
| `manual_labels.csv` | The few items decided by hand, with sources |
| `label_cache.json` | Recorded OpenAlex / doi.org / arXiv responses the labels are built from |
| `http_cache.json` | Recorded registry responses CiteVerify uses on this set |
