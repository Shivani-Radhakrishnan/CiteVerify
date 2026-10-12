"""
Documentation page.
"""
from __future__ import annotations

import streamlit as st

from config import TOK
from utils.ui_helpers import esc, footer, hero, lucide

TIERS = [
    ("01", "calendar", "Temporal check",
     "Extracts the publication year (preferring '(2016)' or a closing year, ignoring page ranges and "
     "identifiers). A year more than one year in the future is impossible and is rejected, with or without a DOI."),
    ("02", "link", "DOI registry",
     "Used when a DOI is supplied or written in the text (arXiv IDs count too). Regular DOIs are resolved via "
     "Crossref, then DataCite; arXiv DOIs via DataCite, then the arXiv API. If no registry has metadata, the "
     "doi.org handle API decides whether the DOI exists at all. The cited title, year and first author are "
     "then compared with the record: any contradiction means the DOI is real but the citation is not."),
    ("03", "search", "Title search",
     "Without a DOI, the citation is searched in Crossref (bibliographic query) and, if no consistent match "
     "is found, arXiv (title terms). Errata and reviews are ignored. A matching title with consistent year and "
     "author verifies the citation; a matching title credited to other people is flagged as misattributed; no "
     "similar title anywhere is treated as likely fabricated."),
    ("04", "sigma", "Heuristic fallback",
     "Only when nothing can be looked up (no usable title, search switched off, or registries unreachable). "
     "Scores surface patterns of the citation text. These describe format, not truthfulness, so this tier "
     "never returns VERIFIED and should be read as 'unknown'."),
]

SCORES = [
    ("≥ 0.70", "VERIFIED", TOK["good"], "A registry record confirms the citation."),
    ("0.20 – 0.69", "UNCERTAIN", TOK["warn"], "Small discrepancy, partial match or nothing checkable: review by hand."),
    ("< 0.20", "HALLUCINATED", TOK["bad"], "Impossible date, non-existent DOI, or details that contradict the registry."),
]


def render() -> None:
    hero(
        "How CiteVerify Works",
        "A tiered pipeline that prefers hard evidence from scholarly registries and says so when it has none.",
        badges=["4 tiers", "Registry-aware DOI routing", "Explainable signals", "Held-out evaluation"],
    )

    for n, icon, name, desc in TIERS:
        with st.expander(f"**Tier {n}** — {name}", expanded=n == "02"):
            st.markdown(f'<span class="cv-ico" style="color:{TOK["accent"]};">{lucide(icon)}</span>',
                        unsafe_allow_html=True)
            st.markdown(desc)

    st.markdown("---")
    st.markdown("### Score interpretation")
    for rng, label, color, note in SCORES:
        st.markdown(
            f'<div class="cv-signal"><div style="font-family:{TOK["mono"]};font-weight:800;color:{color};'
            f'min-width:110px;">{esc(rng)}</div><div style="font-weight:750;min-width:140px;color:{TOK["text"]};">'
            f'{esc(label)}</div><div class="cv-signal-detail">{esc(note)}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption("The HALLUCINATED threshold is adjustable in the sidebar; the benchmark uses 0.20.")

    st.markdown("---")
    st.markdown("### Evaluation")
    st.markdown(
        "Results come from a held-out benchmark of 270 citations (158 correct citations of 79 real papers "
        "with hand-checked DOIs, 112 synthetic fabrications in ten categories), split by paper into a "
        "development and a test half. Registry responses are recorded, so `python -m evaluation.run` "
        "reproduces the numbers offline. See the Analytics page and `evaluation/README.md`, which also "
        "explains why an earlier accuracy figure was withdrawn."
    )

    st.markdown("### Known limitations")
    for limitation in [
        "Works that Crossref, DataCite and arXiv do not index (many books, theses, reports) cannot be "
        "confirmed and may be reported as having no matching record.",
        "Fabricated titles that are close to a real paper's title land in the UNCERTAIN band rather than "
        "being flagged.",
        "Registry metadata has gaps (missing dates, group authors); a field that cannot be compared is "
        "reported as not checked.",
        "The fabricated half of the benchmark is synthetic; real model hallucinations may be subtler.",
    ]:
        st.markdown(
            f'<div class="cv-signal"><span class="cv-ico" style="color:{TOK["warn"]};">{lucide("alert-triangle")}</span>'
            f'<span class="cv-signal-detail">{esc(limitation)}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Python API")
    st.code(
        """from citeverify import Auditor, AuditConfig

auditor = Auditor()  # or Auditor(AuditConfig(use_search=False, threshold=0.3))
result = auditor.audit(
    "Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation.",
    doi="10.1162/neco.1997.9.8.1735",
)
print(result.label, result.score, result.tier)
for signal in result.signals:
    print(signal.status, signal.name, signal.detail)""",
        language="python",
    )

    st.markdown("### Version history")
    with st.expander("**v2.2** — learned risk, REST API, AI-written citations", expanded=True):
        for item in [
            "Calibrated probability of fabrication from a learned model over the collected evidence",
            "REST API (FastAPI) and Docker images for the API and this app",
            "Evaluated on 805 references written by ChatGPT, Gemini and Claude models",
            "arXiv IDs in the DOI field are resolved; better title parsing (abbreviations, quoted phrases)",
        ]:
            st.markdown(f"- {item}")
    with st.expander("**v2.0** — package refactor and held-out evaluation", expanded=False):
        for item in [
            "citeverify package with typed detectors and registry clients (timeouts, retries, caching)",
            "Citation parsing for APA, IEEE and Vancouver styles; title search when no DOI is given",
            "DOI checks now catch future years, use every registry date and handle accents and particles",
            "Held-out benchmark with recorded responses; legacy known-papers table off by default",
        ]:
            st.markdown(f"- {item}")
    with st.expander("**v1.0** — initial release", expanded=False):
        for item in ["4-tier pipeline", "DOI verification (Crossref, DataCite, arXiv)", "Batch, compare and study modes"]:
            st.markdown(f"- {item}")

    st.markdown("### Citing CiteVerify")
    st.code(
        """@software{citeverify,
  title  = {CiteVerify: Citation Hallucination Detection},
  author = {{CiteVerify contributors}},
  year   = {2026},
  url    = {https://github.com/Shivani-Radhakrishnan/CiteVerify}
}""",
        language="bibtex",
    )
    footer("Documentation · transparent methodology")
