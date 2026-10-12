"""
Single Citation Audit page.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from utils.heatmap import highlight_citation
from utils.ui_helpers import (
    comparison_table, esc, evidence_panel, feature_badges, footer, get_auditor, hero, idle_state,
    record_link, section_label, style_label_bg, style_score, tier_stepper, verdict_card,
)

EXAMPLES = [
    ("DOI, details match",
     "He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. "
     "Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition.",
     "10.1109/CVPR.2016.90"),
    ("DOI, wrong year",
     "He, K., Zhang, X., Ren, S., & Sun, J. (2019). Deep residual learning for image recognition. CVPR.",
     "10.1109/CVPR.2016.90"),
    ("No DOI, found by title",
     "Kingma DP, Ba J. Adam: A method for stochastic optimization. arXiv preprint. 2014.", ""),
    ("No DOI, wrong authors",
     "Breiman, L. (2001). Deep residual learning for image recognition. CVPR.", ""),
    ("Invented reference",
     "Ivanova, A. (2017). Diffusion priors: Rethinking soil moisture estimation with scalable objectives. "
     "IEEE Transactions on Pattern Analysis and Machine Intelligence.", ""),
    ("DOI that does not exist",
     'V. Okonkwo and Q. Whitcombe, "Federated token pruning for anomaly detection in power grids," '
     "Proceedings of the AAAI Conference on Artificial Intelligence, 2022.", "10.1145/9792858.9764284"),
    ("Future date", "Chen, X. (2031). Neural scaling laws revisited. NeurIPS.", ""),
]


def _load_example(text: str, doi: str) -> None:
    st.session_state["citation_textarea"] = text
    st.session_state["doi_input"] = doi
    st.session_state["auto_run"] = True


def _clear() -> None:
    for k in ("citation_textarea", "doi_input", "last_result", "last_input"):
        st.session_state.pop(k, None)


def render() -> None:
    hero(
        "Single Citation Audit",
        "Paste a reference, with or without a DOI. CiteVerify checks the date, resolves the DOI or "
        "searches Crossref and arXiv by title, and compares title, year and first author with the record.",
        badges=["DOI resolution", "Title search", "Field-by-field evidence", "PDF export"],
    )

    col_input, col_examples = st.columns([3.4, 1.6], gap="large")

    with col_examples:
        section_label("sliders", "Examples")
        for label, text, doi in EXAMPLES:
            st.button(label, key=f"ex_{label}", use_container_width=True, type="secondary",
                      on_click=_load_example, args=(text, doi))
        st.caption("Examples query the live registries.")

    with col_input:
        section_label("file-text", "Citation")
        st.text_area(
            "Citation text", key="citation_textarea", height=130, label_visibility="collapsed",
            placeholder="e.g. Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation.",
        )
        st.text_input("DOI (optional; a DOI or arXiv ID inside the text is also picked up)", key="doi_input",
                      placeholder="10.1162/neco.1997.9.8.1735  or  https://doi.org/...")
        c1, c2 = st.columns([3, 1])
        with c1:
            clicked = st.button("Run audit", type="primary", use_container_width=True)
        with c2:
            st.button("Clear", type="secondary", use_container_width=True, on_click=_clear)

    text = (st.session_state.get("citation_textarea") or "").strip()
    doi = (st.session_state.get("doi_input") or "").strip()
    run = clicked or st.session_state.pop("auto_run", False)

    if run and not text:
        st.warning("Enter a citation to audit.")
    elif run:
        with st.spinner("Checking registries…"):
            try:
                result = get_auditor().audit(text, doi or None)
            except Exception as exc:  # never show a traceback to the user
                st.error(f"The audit failed unexpectedly: {exc}")
                result = None
        if result is not None:
            st.session_state["last_result"] = result
            st.session_state["last_input"] = (text, doi)
            history = st.session_state.setdefault("audit_history", [])
            history.insert(0, {
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Citation": text[:80] + ("…" if len(text) > 80 else ""),
                "Label": result.label, "Score": round(result.score, 2), "Tier": result.tier,
            })
            del history[10:]

    result = st.session_state.get("last_result")
    if result is None:
        idle_state("Ready to audit", "Enter a citation and press Run audit, or pick an example.")
    else:
        _render_result(result, *st.session_state.get("last_input", ("", "")))

    if st.session_state.get("audit_history"):
        st.markdown("#### Session history")
        hist = pd.DataFrame(st.session_state["audit_history"])
        st.dataframe(hist.style.map(style_label_bg, subset=["Label"]).map(style_score, subset=["Score"]).format({"Score": "{:.2f}"}),
                     width="stretch", hide_index=True)

    footer("CiteVerify · checks are only as complete as Crossref, DataCite and arXiv")


def _render_result(result, text: str, doi: str) -> None:
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    tier_stepper(result)
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    verdict_card(result)

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("#### Evidence")
        evidence_panel(result)
    with right:
        st.markdown("#### Citation vs. registry")
        st.markdown(highlight_citation(text, result), unsafe_allow_html=True)
        st.dataframe(comparison_table(result), width="stretch", hide_index=True)
        record_link(result)

    if result.features and st.session_state.get("show_features", True):
        with st.expander("Heuristic surface features (fallback tier)", expanded=False):
            st.caption("These patterns describe citation format, not truthfulness; they are used only "
                       "when nothing could be looked up.")
            feature_badges(result.features)

    if st.session_state.get("show_compare", True) and result.parsed:
        with st.expander("Input as parsed", expanded=False):
            p = result.parsed
            st.markdown(
                f"Style detected: `{esc(p.style)}` · authors: {esc(', '.join(p.authors) or '—')} · "
                f"year: {esc(p.year or '—')}"
            )
            st.code(p.cleaned or text, language="text")

    try:
        from utils.pdf_generator import generate_pdf_report
        pdf = generate_pdf_report(result, text, doi)
        st.download_button("Download PDF report", data=pdf.getvalue(), mime="application/pdf",
                           file_name=f"citeverify_report_{datetime.now():%Y%m%d_%H%M%S}.pdf")
    except ImportError:
        st.caption("Install reportlab to enable PDF export.")
