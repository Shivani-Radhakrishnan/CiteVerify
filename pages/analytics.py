"""
Analytics Page - System Performance
"""
import streamlit as st
import pandas as pd
import altair as alt
from utils.ui_helpers import hero
from config import TOK


def render():
    """Render the analytics page"""
    # Check if we have real batch data to show
    has_batch = "batch_results" in st.session_state

    hero(
        "System Performance",
        "Benchmark-style reporting: headline metrics, tier-level behavior, and error taxonomy.",
        badges=[
            "Live session data" if has_batch else "Example benchmark data",
            "Tier summaries",
            "Error taxonomy",
        ],
    )

    if has_batch:
        # Use real session data
        df_batch = st.session_state["batch_results"]
        n  = len(df_batch)
        v  = int((df_batch["label"] == "VERIFIED").sum())
        u  = int((df_batch["label"] == "UNCERTAIN").sum())
        h  = int((df_batch["label"] == "HALLUCINATED").sum())
        avg_score = df_batch["score"].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total audited",       n)
        m2.metric("Verified",          f"{v} ({v/n:.0%})")
        m3.metric("Uncertain",         f"{u} ({u/n:.0%})")
        m4.metric("Hallucinated",      f"{h} ({h/n:.0%})")

        st.markdown("---")
        colA, colB = st.columns([1.2, 1.0], gap="large")
        with colA:
            st.markdown("### Score distribution")
            hist_data = pd.DataFrame({"score": df_batch["score"]})
            hist_chart = (
                alt.Chart(hist_data)
                .mark_bar(color=TOK["accent"], opacity=0.75, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("score:Q", bin=alt.Bin(maxbins=20), title="Plausibility score"),
                    y=alt.Y("count():Q", title="Count"),
                    tooltip=["count()"],
                )
                .properties(height=220, background="transparent")
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor=TOK["subtext"], gridColor=TOK["border"], titleColor=TOK["muted"])
            )
            st.altair_chart(hist_chart, use_container_width=True)

        with colB:
            st.markdown("### Tier breakdown")
            tier_counts = df_batch["tier"].value_counts().reset_index()
            tier_counts.columns = ["Tier", "Count"]
            st.dataframe(tier_counts, width='stretch', hide_index=True)

    else:
        # Example / placeholder data with disclaimer
        st.markdown(
            f"""
<div class="cv-softnote" style="margin-bottom:18px;border-color:rgba(245,158,11,0.4);background:rgba(245,158,11,0.06);">
  <strong style="color:{TOK['warn']};">Example benchmark data</strong> — run a batch audit to populate this page with real session metrics.
</div>
""",
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Overall accuracy",        "97.6%", "+35.6% vs baseline")
        m2.metric("Hallucination precision",  "94.7%")
        m3.metric("Hallucination recall",     "90.0%")
        m4.metric("Total citations audited",  "534")

        st.markdown("---")
        colA, colB = st.columns([1.2, 1.0], gap="large")

        with colA:
            st.markdown("### Detection tier performance")
            tier_df = pd.DataFrame({
                "Tier":      ["DOI Registry Match", "DOI Registry Rejection", "Plausibility Scoring"],
                "Citations": [100, 29, 83],
                "Accuracy":  ["100%", "100%", "68.7%"],
                "Method":    ["Crossref/DataCite", "Crossref/DataCite", "Feature scoring"],
            })
            st.dataframe(tier_df, width='stretch', hide_index=True)

        with colB:
            st.markdown("### Confusion matrix (example)")
            st.markdown(
                f"""
<div class="cv-paper" style="font-family:{TOK['mono']};font-size:12px;padding:16px;">
  <div style="display:grid;grid-template-columns:110px 1fr 1fr;gap:6px;text-align:center;">
    <div></div>
    <div style="color:{TOK['muted']};padding:8px;font-size:11px;">PRED: REAL</div>
    <div style="color:{TOK['muted']};padding:8px;font-size:11px;">PRED: FAKE</div>
    <div style="color:{TOK['muted']};padding:8px;text-align:left;font-size:11px;">ACT: REAL</div>
    <div style="background:rgba(34,197,94,0.14);border:1px solid rgba(34,197,94,0.25);
      border-radius:12px;padding:16px;font-size:24px;font-weight:900;color:#86efac;">142</div>
    <div style="background:rgba(239,68,68,0.14);border:1px solid rgba(239,68,68,0.25);
      border-radius:12px;padding:16px;font-size:24px;font-weight:900;color:#fca5a5;">3</div>
    <div style="color:{TOK['muted']};padding:8px;text-align:left;font-size:11px;">ACT: FAKE</div>
    <div style="background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.25);
      border-radius:12px;padding:16px;font-size:24px;font-weight:900;color:#fcd34d;">2</div>
    <div style="background:rgba(34,197,94,0.14);border:1px solid rgba(34,197,94,0.25);
      border-radius:12px;padding:16px;font-size:24px;font-weight:900;color:#86efac;">65</div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### Residual error modes")
    errors_df = pd.DataFrame([
        {"ID": "CIT_010", "Type": "False positive",  "Issue": "Borderline at threshold",       "Fix": "Manual review for scores near threshold"},
        {"ID": "CIT_013", "Type": "False negative",  "Issue": "Year-first cutoff/author missing","Fix": "Widen extraction window"},
        {"ID": "CIT_021", "Type": "False negative",  "Issue": "Year-first cutoff/author missing","Fix": "Widen extraction window"},
        {"ID": "CIT_064", "Type": "False positive",  "Issue": "Hallucinated arXiv-like ID",     "Fix": "Add external scholarly lookup"},
        {"ID": "CIT_614", "Type": "False positive",  "Issue": "Exactly at threshold",           "Fix": "Boundary-case review"},
    ])
    st.dataframe(errors_df, width='stretch', hide_index=True)

    # Session statistics
    if has_batch:
        st.markdown("---")
        st.markdown("### Session Statistics")
        
        # Time series of audits (if we had timestamps)
        st.markdown("**Audit Performance Over Time**")
        st.info("Time series tracking will be added in a future update.")
        
        # Score distribution by tier
        st.markdown("**Score Distribution by Detection Tier**")
        tier_score_data = []
        for tier in df_batch["tier"].unique():
            tier_data = df_batch[df_batch["tier"] == tier]["score"]
            for score in tier_data:
                tier_score_data.append({"Tier": tier, "Score": score})
        
        if tier_score_data:
            tier_df = pd.DataFrame(tier_score_data)
            tier_chart = (
                alt.Chart(tier_df)
                .mark_boxplot(extent='min-max', opacity=0.7)
                .encode(
                    x=alt.X('Tier:N', title='Detection Tier'),
                    y=alt.Y('Score:Q', title='Plausibility Score', scale=alt.Scale(domain=[0, 1])),
                    color=alt.Color('Tier:N', legend=None)
                )
                .properties(height=300, background="transparent")
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor=TOK["subtext"], gridColor=TOK["border"], titleColor=TOK["muted"])
            )
            st.altair_chart(tier_chart, use_container_width=True)

    st.markdown(
        f"""
<hr>
<div style="text-align:center;color:{TOK['muted']};font-family:{TOK['mono']};font-size:11px;">
  Analytics · session-driven insights
</div>
""",
        unsafe_allow_html=True,
    )