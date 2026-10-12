"""
Study mode: evaluate CiteVerify on your own labelled dataset.
"""
from __future__ import annotations

from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from citeverify.metrics import binary_metrics
from config import TOK
from pages.batch_audit import MAX_ROWS, _clean_doi, _run
from utils.ui_helpers import footer, hero, idle_state


def render() -> None:
    hero(
        "Study Mode",
        "Upload citations with ground-truth labels to measure accuracy, inspect the score distribution "
        "and see how the threshold trades precision for recall on your data.",
        badges=["Ground-truth metrics", "Confusion matrix", "Threshold sweep"],
    )
    st.markdown(
        '<div class="cv-softnote" style="margin-bottom:16px;">'
        "CSV columns: <b>citation</b> and <b>human_label</b> (0 = real, 1 = fabricated); optional <b>doi</b>. "
        "The reference benchmark lives in <code>data/benchmark/benchmark.csv</code> and is scored offline by "
        "<code>python -m evaluation.run</code>.</div>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload labelled CSV", type=["csv"])
    if not uploaded:
        idle_state("Study mode ready", "Upload a CSV with citation and human_label columns.", icon="graduation-cap")
        footer("Study mode · bring your own labels")
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read the CSV: {exc}")
        return
    missing = [c for c in ("citation", "human_label") if c not in df.columns]
    if missing:
        st.error(f"Missing column(s): {', '.join(missing)}")
        return
    df["human_label"] = pd.to_numeric(df["human_label"], errors="coerce")
    df = df[df["human_label"].isin([0, 1])].head(MAX_ROWS).reset_index(drop=True)
    if df.empty:
        st.error("No rows with a 0/1 human_label.")
        return
    st.success(f"{len(df)} labelled citations loaded ({int(df['human_label'].sum())} fabricated).")
    with st.expander("Preview", expanded=False):
        st.dataframe(df.head(10), width="stretch")

    if st.button("Run evaluation", type="primary", use_container_width=True):
        items = [(str(r["citation"]), _clean_doi(r.get("doi")) if "doi" in df.columns else None)
                 for _, r in df.iterrows()]
        res = _run(items)
        res["human_label"] = df["human_label"].astype(int).values
        st.session_state["study_results"] = res

    res = st.session_state.get("study_results")
    if res is None or len(res) != len(df):
        return

    threshold = float(st.session_state.get("threshold", 0.20))
    y_true = res["human_label"].tolist()
    scores = res["score"].astype(float).to_numpy()
    m = binary_metrics(y_true, (scores < threshold).astype(int).tolist())

    st.markdown("### Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{m['accuracy']:.1%}")
    c2.metric("Precision", f"{m['precision']:.1%}")
    c3.metric("Recall", f"{m['recall']:.1%}")
    c4.metric("F1", f"{m['f1']:.1%}")
    cm = m["confusion"]
    st.caption(f"Threshold {threshold:.2f} · positive class = fabricated · "
               f"TP {cm['tp']} · FP {cm['fp']} · FN {cm['fn']} · TN {cm['tn']}")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Confusion matrix")
        cm_df = pd.DataFrame([
            {"Actual": "Real", "Predicted": "Real", "n": cm["tn"]},
            {"Actual": "Real", "Predicted": "Fabricated", "n": cm["fp"]},
            {"Actual": "Fabricated", "Predicted": "Real", "n": cm["fn"]},
            {"Actual": "Fabricated", "Predicted": "Fabricated", "n": cm["tp"]},
        ])
        base = alt.Chart(cm_df).encode(x=alt.X("Predicted:N", sort=["Real", "Fabricated"]),
                                       y=alt.Y("Actual:N", sort=["Real", "Fabricated"]))
        heat = base.mark_rect(cornerRadius=6).encode(
            color=alt.Color("n:Q", scale=alt.Scale(range=["#EEF1F6", TOK["accent"]]), legend=None))
        labels = base.mark_text(fontSize=22, fontWeight="bold").encode(
            text="n:Q", color=alt.condition("datum.n > 0", alt.value("#FFFFFF"), alt.value(TOK["muted"])))
        st.altair_chart((heat + labels).properties(height=260), use_container_width=True)
    with right:
        st.markdown("#### Score distribution")
        dist = res.assign(cls=np.where(res["human_label"] == 1, "Fabricated", "Real"))
        hist = (alt.Chart(dist).mark_bar(opacity=0.75)
                .encode(x=alt.X("score:Q", bin=alt.Bin(maxbins=20), title="Score"),
                        y=alt.Y("count():Q", stack=None, title="Citations"),
                        color=alt.Color("cls:N", scale=alt.Scale(domain=["Real", "Fabricated"],
                                                                 range=[TOK["good"], TOK["bad"]]), title=None)))
        rule = alt.Chart(pd.DataFrame({"t": [threshold]})).mark_rule(color=TOK["text"], strokeDash=[4, 4]).encode(x="t:Q")
        st.altair_chart((hist + rule).properties(height=260), use_container_width=True)

    st.markdown("#### Threshold sweep")
    sweep = []
    for t in np.round(np.arange(0.05, 0.96, 0.05), 2):
        mt = binary_metrics(y_true, (scores < t).astype(int).tolist())
        sweep += [{"threshold": t, "metric": k.title(), "value": mt[k]} for k in ("precision", "recall", "f1")]
    sweep_df = pd.DataFrame(sweep)
    st.altair_chart(
        alt.Chart(sweep_df).mark_line(point=True)
        .encode(x="threshold:Q", y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1])), color="metric:N")
        .properties(height=280), use_container_width=True,
    )
    best = sweep_df[sweep_df["metric"] == "F1"].sort_values("value", ascending=False).iloc[0]
    st.caption(f"Highest F1 on this file: {best['value']:.3f} at threshold {best['threshold']:.2f}. "
               "Choosing a threshold on the same data you report on overstates performance; "
               "hold out part of your data.")

    st.markdown("#### Per-row results")
    st.dataframe(res, width="stretch", hide_index=True)
    st.download_button("Download results (CSV)", res.to_csv(index=False),
                       f"study_results_{datetime.now():%Y%m%d_%H%M%S}.csv", "text/csv", use_container_width=True)
    footer("Study mode · bring your own labels")
