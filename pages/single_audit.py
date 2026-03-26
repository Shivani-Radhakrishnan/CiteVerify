"""
Single Citation Audit Page
"""
from unittest import result

import streamlit as st
import inspect
from utils.ui_helpers import (
    hero, verdict_card, evidence_panel, feature_badges, 
    style_label_bg, style_score, lucide
)
from utils.auditor import audit_citation, extract_core_citation
from config import TOK
from datetime import datetime


def render():
    """Render the single audit page"""
    hero(
        "Single Citation Audit",
        "Paste a citation string and receive a research-grade verdict with a transparent, tiered pipeline trail.",
        badges=["Inline-fragment aware", "DOI registry verification", "Explainable signals", "PDF export"],
    )

    # Slightly wider input column; examples remain readable but compact.
    col_input, col_examples = st.columns([3.4, 1.6], gap="large")

    examples = [
        ("Known real paper", "vaswani a 2017 attention is all you need"),
        ("Known fake paper", "ji z 2023 survey of hallucination"),
        ("Future date", "Chen X 2029 neural scaling laws revised"),
        ("Inline fragment", "geiping et al 2025 or null"),
        ("Reference-style entry", "lewis p liu y 2020 retrieval augmented generation acl"),
    ]

    with col_examples:
        # Keep the whole examples area as ONE cohesive card to avoid misalignment
        # caused by Streamlit's default widget spacing.
        st.markdown(
            f"""
<div class="cv-paper cv-examples-card">
  <div class="cv-examples-head">
    <span class="cv-ico" style="color:{TOK['accent']};">{lucide('sliders')}</span>
    <span>Quick examples</span>
  </div>
""",
            unsafe_allow_html=True,
        )

        for label, ex in examples:
            st.markdown('<div class="ex-btn">', unsafe_allow_html=True)
            if st.button(label, key=f"ex_{label}", use_container_width=True):
                # IMPORTANT: update the widget state directly so the textarea
                # visibly changes on click (Streamlit ignores `value=` once
                # the widget has state).
                st.session_state["citation_val"] = ex
                st.session_state["citation_textarea"] = ex
                # Clear DOI when switching examples (presentation convenience only)
                st.session_state["doi_input"] = ""
                st.session_state["auto_run"] = True
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f"""
  <div class="cv-softnote" style="margin-top:12px;">
    Provide a DOI for high-confidence registry verification when available.
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    stored_text = st.session_state.get("citation_val", "")

    with col_input:
        st.markdown(
            f"""
<div style="font-family:{TOK['mono']};font-size:10.5px;text-transform:uppercase;
  letter-spacing:1.2px;color:{TOK['muted']};margin-bottom:8px;display:flex;align-items:center;gap:6px;">
  <span class="cv-ico" style="color:{TOK['accent']};">{lucide('file-text')}</span>
  <span>Citation input</span>
</div>
""",
            unsafe_allow_html=True,
        )

        citation_text = st.text_area(
            "Citation text",
            value=stored_text,
            height=130,
            placeholder=(
                "e.g. vaswani a shazeer n 2017 attention is all you need\n"
                "or:  As shown by Geiping et al. 2025 or null\n"
                "or:  ji z 2023 survey of hallucination"
            ),
            key="citation_textarea",
            label_visibility="collapsed",
        )
        st.session_state["citation_val"] = citation_text

        doi_input = st.text_input(
            "DOI (optional)",
            placeholder="e.g. 10.1145/3219819.3220080  or  10.48550/arXiv.1706.03762",
            key="doi_input",
        )

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            clicked_audit = st.button("Run audit", use_container_width=True)
        with c2:
            # Prefer Streamlit's secondary button styling (when available) to keep
            # baseline alignment and avoid wrapper-induced vertical offsets.
            btn_kwargs = {"use_container_width": True}
            if "type" in inspect.signature(st.button).parameters:
                btn_kwargs["type"] = "secondary"

            if st.button("Clear", **btn_kwargs):
                for k in ("audit_history", "citation_val", "auto_run", "last_result"):
                    st.session_state.pop(k, None)
                st.rerun()
        with c3:
            # PDF Export button
            if st.session_state.get("last_result"):
                btn2_kwargs = {"use_container_width": True}
                if "type" in inspect.signature(st.button).parameters:
                    btn2_kwargs["type"] = "secondary"

                if st.button("Export PDF", **btn2_kwargs):
                    from utils.pdf_generator import generate_pdf_report
                    result = st.session_state["last_result"]
                    pdf_buffer = generate_pdf_report(
                        result, citation_text, doi_input,
                        st.session_state.get("run_id", ""),
                        st.session_state.get("config_hash", "")
                    )
                    st.download_button(
                        label="Download PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"citeverify_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )

    # Quick examples should run immediately after click.
    # (UI-only behavior; does not alter any scoring / routing logic.)
    auto_run = st.session_state.pop("auto_run", False)
    run_audit = clicked_audit or auto_run
    active_text = (citation_text or "").strip()

    if run_audit and active_text:
        with st.status("Running audit pipeline…", expanded=True) as status:
            st.write("01 · Checking DOI registry (if provided)…")
            st.write("02 · Temporal sanity check…")
            st.write("03 · Known-papers database lookup…")
            st.write("04 · Feature-based plausibility scoring…")
            result = audit_citation(active_text, doi_input.strip() or None)
            st.session_state["last_result"] = result
            status.update(label="Audit complete", state="complete")

    elif run_audit and not active_text:
        st.warning("Please enter a citation string to audit.")

    # ── Results area ──
    result = st.session_state.get("last_result", None)

    if result:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        from utils.ui_helpers import tier_stepper
        tier_stepper(result.tier)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        verdict_card(result)
        from utils.heatmap import highlight_citation

        st.markdown("### Citation Inspection")

        heat_html = highlight_citation(active_text, result)

        st.markdown(heat_html, unsafe_allow_html=True)



        # Evidence Panel
        from utils.ui_helpers import evidence_panel_safe

        with st.expander("Evidence breakdown", expanded=True):
            evidence_panel_safe(result, active_text)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Plausibility", f"{result.score:.3f}")
        m2.metric("Label", result.label)
        m3.metric("Tier", st.session_state.get("_tier_num", lambda x: "—")(result.tier))
        m4.metric("Method", result.tier[:22] + ("…" if len(result.tier) > 22 else ""))

        if st.session_state.get("show_compare", True):
            with st.expander("Input normalization — original vs cleaned", expanded=False):
                cleaned = extract_core_citation(active_text)
                cL, cR = st.columns(2)
                with cL:
                    st.markdown("**Original input**")
                    st.code(active_text, language="text")
                with cR:
                    st.markdown("**Cleaned text fed to scorer**")
                    st.code(cleaned, language="text")

        if st.session_state.get("show_features", True) and getattr(result, "features", None):
            with st.expander("Feature signals — interpretable breakdown", expanded=False):
                feature_badges(result.features)

        # Save to session history
        if "audit_history" not in st.session_state:
            st.session_state.audit_history = []
        entry = {
            "Citation": active_text[:80] + ("…" if len(active_text) > 80 else ""),
            "Score": round(result.score, 3),
            "Label": result.label,
            "Tier": st.session_state.get("_tier_num", lambda x: "—")(result.tier),
        }
        # Avoid duplicate on rerender
        if not st.session_state.audit_history or st.session_state.audit_history[0]["Citation"] != entry["Citation"]:
            st.session_state.audit_history.insert(0, entry)
            st.session_state.audit_history = st.session_state.audit_history[:10]

    else:
        # Idle / empty state
        st.markdown(
            f"""
<div class="cv-idle-state">
  <div style="margin-bottom:14px;opacity:0.7;color:{TOK['accent']};" class="cv-ico">{lucide('flask-conical')}</div>
  <div style="font-weight:700;font-size:15px;color:{TOK['subtext']};margin-bottom:6px;">
    Ready to audit
  </div>
  <div style="font-size:13px;color:{TOK['muted']};max-width:38ch;line-height:1.6;">
    Enter a citation above and click <strong style="color:{TOK['accent']}">Run Audit</strong>,
    or pick a quick example on the right.
  </div>
  <div style="margin-top:20px;display:flex;gap:12px;flex-wrap:wrap;justify-content:center;">
    <span class="cv-badge">VERIFIED</span>
    <span class="cv-badge">UNCERTAIN</span>
    <span class="cv-badge">HALLUCINATED</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ── Session history ──
    if st.session_state.get("audit_history"):
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="cv-section-header">
  <div style="font-weight:700;font-size:14.5px;color:{TOK['text']};">
    Session history <span style="font-size:12px;color:{TOK['muted']};font-weight:400;">
      (last {len(st.session_state.audit_history)})
    </span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        import pandas as pd
        hist_df = pd.DataFrame(st.session_state.audit_history)
        st.dataframe(
            hist_df.style
                .map(style_label_bg, subset=["Label"])
                .map(style_score, subset=["Score"]),
            width='stretch',
            hide_index=True,
        )

    st.markdown(
        f"""
<hr>
<div style="text-align:center;color:{TOK['muted']};font-family:{TOK['mono']};font-size:11px;">
  CiteVerify · research UI · transparent, tiered verification
</div>
""",
        unsafe_allow_html=True,
    )