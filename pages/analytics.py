"""
Analytics page: benchmark results and the current session's batch.
"""
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from config import TOK
from utils.ui_helpers import footer, hero

RESULTS = Path(__file__).resolve().parent.parent / "evaluation" / "results" / "test.json"
SYSTEM_NAMES = {
    "v1": "v1 (original engine)",
    "v1_no_table": "v1 without known-papers table",
    "v2": "v2 (current engine)",
    "v2_with_table": "v2 with known-papers table",
    "v2_no_search": "v2 without title search",
}


@st.cache_data(show_spinner=False)
def load_benchmark() -> dict | None:
    try:
        return json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def render() -> None:
    hero(
        "System Performance",
        "Held-out benchmark results (reproducible with python -m evaluation.run) and statistics for the "
        "batch you audited in this session.",
        badges=["Held-out test split", "Ablations", "Per-tier accuracy"],
    )
    tab_bench, tab_session = st.tabs(["Benchmark", "This session"])
    with tab_bench:
        _benchmark()
    with tab_session:
        _session()
    footer("Analytics · numbers come from evaluation/results/test.json")


def _benchmark() -> None:
    report = load_benchmark()
    if report is None:
        st.warning("evaluation/results/test.json not found. Run `python -m evaluation.run --split test`.")
        return
    v2 = report["systems"]["v2"]["overall"]
    st.caption(f"Test split: {report['n_items']} citations ({report['n_real']} real, {report['n_fabricated']} "
               f"synthetic fabrications), none overlapping the legacy known-papers table. "
               f"Threshold {report['threshold']:.2f}; positive class = fabricated.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy", f"{v2['accuracy']:.1%}")
    m2.metric("Precision", f"{v2['precision']:.1%}")
    m3.metric("Recall", f"{v2['recall']:.1%}")
    m4.metric("False-positive rate", f"{v2['false_positive_rate']:.1%}")

    rows = []
    for key, s in report["systems"].items():
        o, r = s["overall"], s["review_mode"]
        rows.append({"System": SYSTEM_NAMES.get(key, key), "Accuracy": o["accuracy"], "Precision": o["precision"],
                     "Recall": o["recall"], "F1": o["f1"], "FPR": o["false_positive_rate"],
                     "Recall (review mode)": r["recall"], "FPR (review mode)": r["false_positive_rate"]})
    table = pd.DataFrame(rows)
    st.markdown("#### Systems and ablations")
    st.dataframe(table.style.format({c: "{:.1%}" for c in table.columns if c != "System"}),
                 width="stretch", hide_index=True)
    st.caption("Review mode also counts UNCERTAIN (\"check by hand\") as a detection.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Per detection tier (v2)")
        tiers = pd.DataFrame([{"Tier": t, "Citations": v["n"], "Real": v["real"], "Fabricated": v["fabricated"],
                               "Correct": f"{v['correct']}/{v['n']}"}
                              for t, v in report["systems"]["v2"]["by_tier"].items()])
        st.dataframe(tiers, width="stretch", hide_index=True)
    with right:
        st.markdown("#### Per category, correct (v1 vs v2)")
        cats = []
        for c, v in report["systems"]["v2"]["by_category"].items():
            for key in ("v1", "v2"):
                cv = report["systems"][key]["by_category"][c]
                cats.append({"Category": c, "System": key, "Correct": cv["correct"] / cv["n"]})
        chart = (alt.Chart(pd.DataFrame(cats)).mark_bar()
                 .encode(y=alt.Y("Category:N", title=None), x=alt.X("Correct:Q", axis=alt.Axis(format="%")),
                         yOffset="System:N",
                         color=alt.Color("System:N", scale=alt.Scale(range=[TOK["muted"], TOK["accent"]])))
                 .properties(height=360))
        st.altair_chart(chart, use_container_width=True)

    probe = report.get("probe")
    if probe:
        st.markdown("#### Known-papers table probe")
        st.caption(f"{probe['n']} correct citations of real papers whose first authors are in the legacy "
                   "table. Lower is better: these should never be flagged.")
        st.dataframe(pd.DataFrame([{"System": SYSTEM_NAMES.get(k, k), "Flagged (as written)": v["raw"],
                                    "Flagged (lower-case)": v["lowercase"]} for k, v in probe["flagged"].items()]),
                     width="stretch", hide_index=True)


def _session() -> None:
    df = st.session_state.get("batch_results")
    if df is None or df.empty:
        st.info("Run a batch audit to see statistics for your own citations here.")
        return
    n = len(df)
    counts = df["label"].value_counts()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Audited", n)
    for col, lab in zip((m2, m3, m4), ("VERIFIED", "UNCERTAIN", "HALLUCINATED")):
        c = int(counts.get(lab, 0))
        col.metric(lab.title(), f"{c} ({c / n:.0%})")
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown("#### Score distribution")
        st.altair_chart(
            alt.Chart(df).mark_bar(color=TOK["accent"], opacity=0.8)
            .encode(x=alt.X("score:Q", bin=alt.Bin(maxbins=20), title="Score"), y=alt.Y("count():Q", title="Count"))
            .properties(height=240), use_container_width=True)
    with right:
        st.markdown("#### Deciding tier")
        tier_counts = df["tier"].value_counts().rename_axis("Tier").reset_index(name="Citations")
        st.dataframe(tier_counts, width="stretch", hide_index=True)
