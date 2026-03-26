"""
Batch Citation Audit Page
"""
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from utils.ui_helpers import hero, style_label_bg, style_score
from utils.auditor import audit_citation
from config import TOK


def render():
    """Render the batch audit page"""
    hero(
        "Batch Citation Audit",
        "Bulk-audit citations from CSV or pasted lines. Designed as a reproducible evaluation workflow.",
        badges=["Step-based workflow", "Summary chart + filters", "CSV export", "Error analysis lab"],
    )

    # Step indicator
    st.markdown(
        f"""
<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:20px;">
  <div style="display:flex;align-items:center;gap:8px;padding:9px 16px;
    background:rgba(96,165,250,0.12);border:1px solid rgba(96,165,250,0.4);
    border-radius:10px;font-weight:700;font-size:13px;">
    <span style="color:{TOK['accent']};">1</span>
    <span style="color:{TOK['text']};">Upload / Paste</span>
  </div>
  <div style="width:28px;height:2px;background:{TOK['border']};"></div>
  <div style="display:flex;align-items:center;gap:8px;padding:9px 16px;
    background:rgba(8,14,28,0.35);border:1px solid {TOK['border']};
    border-radius:10px;font-weight:600;font-size:13px;color:{TOK['muted']};">
    <span>2</span><span>Configure</span>
  </div>
  <div style="width:28px;height:2px;background:{TOK['border']};"></div>
  <div style="display:flex;align-items:center;gap:8px;padding:9px 16px;
    background:rgba(8,14,28,0.35);border:1px solid {TOK['border']};
    border-radius:10px;font-weight:600;font-size:13px;color:{TOK['muted']};">
    <span>3</span><span>Review results</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    tab_csv, tab_paste = st.tabs(["CSV upload", "Paste text"])

    with tab_csv:
        st.markdown(
            f"""
<div class="cv-softnote" style="margin-bottom:16px;">
  Expected CSV columns:<br>
  &nbsp;• <b>citation</b> / <b>claimed_content</b> / <b>text</b> (required)<br>
  &nbsp;• <b>doi</b> (optional — enables registry verification)<br>
  &nbsp;• <b>human_label</b> (optional: 0=real, 1=fake) for evaluation
</div>
""",
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            df_up = pd.read_csv(uploaded)
            st.caption(f"Loaded **{len(df_up)} rows** · Columns: `{list(df_up.columns)}`")

            default_text_col = next(
                (c for c in ["citation", "claimed_content", "text", "reference"] if c in df_up.columns),
                df_up.columns[0],
            )
            default_doi_col = next((c for c in ["doi", "DOI", "claimed_doi"] if c in df_up.columns), None)

            cfg1, cfg2 = st.columns([2, 1], gap="large")
            with cfg1:
                text_col = st.selectbox(
                    "Citation text column",
                    df_up.columns.tolist(),
                    index=list(df_up.columns).index(default_text_col),
                )
            with cfg2:
                use_doi = False
                if default_doi_col:
                    use_doi = st.checkbox(
                        f"Use DOI column (`{default_doi_col}`)",
                        value=True,
                    )

            if st.button("Run batch audit", use_container_width=True):
                prog = st.progress(0, text="Initializing…")
                live_table = st.empty()
                results = []
                n = len(df_up)

                for i, (_, row) in enumerate(df_up.iterrows()):
                    txt = str(row.get(text_col, "")).strip()
                    raw_doi = row.get(default_doi_col, "") if (use_doi and default_doi_col) else ""
                    if pd.isna(raw_doi) or str(raw_doi).strip().lower() in ("", "nan", "none", "n/a", "-"):
                        d = None
                    else:
                        d = str(raw_doi).strip()

                    r = audit_citation(txt, d)
                    results.append({
                        "citation": txt[:90],
                        "score":    round(r.score, 3),
                        "label":    r.label,
                        "tier":     r.tier,
                        "action":   r.action,
                    })
                    prog.progress((i + 1) / n, text=f"Auditing {i+1} / {n}…")

                    # Live preview every 5 rows
                    if (i + 1) % 5 == 0 or (i + 1) == n:
                        preview_df = pd.DataFrame(results)
                        live_table.dataframe(
                            preview_df.style
                            .map(style_label_bg, subset=["label"])
                            .map(style_score,    subset=["score"])
                            .format({"score": "{:.3f}"}),
                        use_container_width=True,
                        hide_index=True,
                    )

                prog.empty()
                live_table.empty()
                st.session_state["batch_results"] = pd.DataFrame(results)
                if "human_label" in df_up.columns:
                    st.session_state["batch_labels"] = df_up["human_label"].values
                st.success(f"Audited {n} citations. Scroll down to review results.")

    with tab_paste:
        pasted = st.text_area(
            "One citation per line",
            height=200,
            placeholder=(
                "Vaswani et al. (2017) Attention Is All You Need\n"
                "Lewis et al. (2020) Retrieval-Augmented Generation\n"
                "Smith 2024 quantum ethics in AI NeurIPS"
            ),
        )
        if st.button("Audit pasted citations", use_container_width=True) and pasted.strip():
            lines = [l.strip() for l in pasted.splitlines() if l.strip()]
            results = []
            prog2 = st.progress(0, text="Initializing…")
            for i, line in enumerate(lines):
                r = audit_citation(line)
                results.append({
                    "citation": line[:90],
                    "score":    round(r.score, 3),
                    "label":    r.label,
                    "tier":     r.tier,
                    "action":   r.action,
                })
                prog2.progress((i + 1) / len(lines), text=f"Auditing {i+1} / {len(lines)}…")
            prog2.empty()
            st.session_state["batch_results"] = pd.DataFrame(results)
            st.success(f"Audited {len(lines)} citations.")

    # ── Results ──
    if "batch_results" in st.session_state:
        df_res = st.session_state["batch_results"]
        st.markdown("---")
        st.markdown(
            f'<div style="font-size:1.1rem;font-weight:800;color:{TOK["text"]};margin-bottom:14px;">Results</div>',
            unsafe_allow_html=True,
        )

        n = len(df_res)
        v = int((df_res["label"] == "VERIFIED").sum())
        u = int((df_res["label"] == "UNCERTAIN").sum())
        h = int((df_res["label"] == "HALLUCINATED").sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", n)
        m2.metric("Verified",     f"{v} ({v/n:.0%})" if n else "0")
        m3.metric("Uncertain",    f"{u} ({u/n:.0%})" if n else "0")
        m4.metric("Hallucinated", f"{h} ({h/n:.0%})" if n else "0")

        chart_df = pd.DataFrame({
            "label": ["VERIFIED", "UNCERTAIN", "HALLUCINATED"],
            "count": [v, u, h],
            "color": [TOK["good"], TOK["warn"], TOK["bad"]],
        })

        cL, cR = st.columns([1.1, 1.9], gap="large")
        with cL:
            st.markdown("**Distribution**")
            pie = (
                alt.Chart(chart_df)
                .mark_arc(innerRadius=52, outerRadius=100, stroke="#0c1526", strokeWidth=2)
                .encode(
                    theta=alt.Theta("count:Q"),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(
                            domain=["VERIFIED", "UNCERTAIN", "HALLUCINATED"],
                            range=[TOK["good"], TOK["warn"], TOK["bad"]],
                        ),
                        legend=alt.Legend(
                            orient="bottom",
                            title=None,
                            labelColor=TOK["subtext"],
                            labelFontSize=12,
                            symbolSize=120,
                            padding=10,
                            offset=10,
                        ),
                    ),
                    tooltip=["label", "count"],
                )
                # ✅ THE IMPORTANT PART: explicit padding + more height
                .properties(
                    height=340,
                    padding={"top": 29, "left": 10, "right": 10, "bottom": 28},
                    background="transparent",
                )
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(pie, use_container_width=True)
        with cR:
            st.markdown("**Review & filter**")
            fc, sc, tc = st.columns([1.3, 1.1, 1.2])
            with fc:
                filt = st.selectbox("Filter", ["All", "VERIFIED", "UNCERTAIN", "HALLUCINATED"])
            with sc:
                asc = st.checkbox("Sort ↑ score", value=True)
            with tc:
                show_actions = st.checkbox("Show actions", value=True)

            disp = df_res if filt == "All" else df_res[df_res["label"] == filt]
            disp = disp.sort_values("score", ascending=asc)
            if not show_actions:
                disp = disp.drop(columns=["action"], errors="ignore")

            st.dataframe(
                disp.style
                    .map(style_label_bg, subset=["label"])
                    .map(style_score,    subset=["score"])
                    .format({"score": "{:.3f}"}),
                width='stretch',
                hide_index=True,
            )

        st.download_button(
            "Download results as CSV",
            df_res.to_csv(index=False).encode("utf-8"),
            "citeverify_results.csv",
            "text/csv",
            use_container_width=True,
        )

        # Error Analysis Lab
        st.markdown("---")
        st.markdown("### Error analysis")
        
        # Borderline cases
        threshold_val = st.session_state.get("threshold", 0.20)
        borderline = df_res[
            (df_res["score"] >= threshold_val - 0.05) & 
            (df_res["score"] <= threshold_val + 0.05)
        ]
        
        with st.expander("Borderline cases (±0.05 of threshold)", expanded=False):
            if len(borderline) > 0:
                st.dataframe(borderline, width='stretch', hide_index=True)
            else:
                st.info("No borderline cases found.")
        
        # Clusters
        with st.expander("Error clusters", expanded=False):
            # Year issues
            year_issues = df_res[df_res["tier"].str.contains("temporal", case=False, na=False)]
            st.markdown("**Temporal Issues:**")
            st.dataframe(year_issues, width='stretch', hide_index=True)
            
            # Reference-entry style
            ref_style = df_res[df_res["tier"].str.contains("plausibility", case=False, na=False)]
            st.markdown("**Reference Entry Style:**")
            st.dataframe(ref_style, width='stretch', hide_index=True)
        
        # Evaluation vs ground truth
        if "batch_labels" in st.session_state:
            lbls = st.session_state["batch_labels"]
            if len(lbls) == len(df_res):
                st.markdown("---")
                st.markdown("### Evaluation vs `human_label`")
                st.caption(f"Prediction rule: `score < {threshold_val} → hallucination`")
                try:
                    from sklearn.metrics import classification_report
                    preds = (df_res["score"] < threshold_val).astype(int)
                    report = classification_report(
                        lbls, preds,
                        target_names=["Real (0)", "Hallucination (1)"],
                        output_dict=True,
                    )
                    rep_df = pd.DataFrame(report).T
                    st.dataframe(rep_df.style.format("{:.3f}"), width='stretch')
                except Exception as e:
                    st.warning(f"Could not compute metrics: {e}")

    st.markdown(
        f"""
<hr>
<div style="text-align:center;color:{TOK['muted']};font-family:{TOK['mono']};font-size:11px;">
  Batch workflow · exportable · reproducible
</div>
""",
        unsafe_allow_html=True,
    )