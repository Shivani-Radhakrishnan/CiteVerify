"""
Batch Citation Audit page.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from citeverify.metrics import binary_metrics
from citeverify.parsing import normalise_doi
from config import TOK
from utils.ui_helpers import footer, get_auditor, hero, idle_state, style_label_bg, style_score

TEXT_COLUMNS = ["citation", "claimed_content", "text", "reference"]
DOI_COLUMNS = ["doi", "DOI", "claimed_doi"]
MAX_ROWS = 500


def _clean_doi(value) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    return normalise_doi(value)


def _run(items: list[tuple[str, Optional[str]]]) -> pd.DataFrame:
    """Audit ``(text, doi)`` pairs on a small thread pool with a progress bar."""
    auditor = get_auditor()
    results: list[Optional[dict]] = [None] * len(items)
    prog = st.progress(0.0, text="Starting…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(auditor.audit, t, d): i for i, (t, d) in enumerate(items)}
        for done, fut in enumerate(as_completed(futures), 1):
            i = futures[fut]
            text = items[i][0]
            try:
                r = fut.result()
                row = {"citation": text, **r.to_row()}
            except Exception as exc:  # one bad row must not kill the batch
                row = {"citation": text, "label": "UNCERTAIN", "score": 0.5, "verdict": "Error",
                       "reason": "Audit failed", "tier": "", "explanation": str(exc), "action": "",
                       "matched_doi": "", "error": str(exc)}
            results[i] = row
            prog.progress(done / len(items), text=f"Audited {done} / {len(items)}")
    prog.empty()
    return pd.DataFrame(results)


def render() -> None:
    hero(
        "Batch Citation Audit",
        "Audit a reference list from a CSV file or pasted lines. Results can be filtered, exported, and "
        "scored against your own labels.",
        badges=["CSV or paste", "Parallel registry lookups", "CSV export", "Metrics vs. your labels"],
    )

    tab_csv, tab_paste = st.tabs(["CSV upload", "Paste text"])

    with tab_csv:
        st.markdown(
            '<div class="cv-softnote" style="margin-bottom:16px;">'
            "Columns: <b>citation</b> (or claimed_content / text / reference, required), "
            "<b>doi</b> (optional), <b>human_label</b> (optional: 0 = real, 1 = fabricated). "
            f"Up to {MAX_ROWS} rows.</div>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            try:
                df_up = pd.read_csv(uploaded)
            except Exception as exc:
                st.error(f"Could not read the CSV: {exc}")
                df_up = None
            if df_up is not None and df_up.empty:
                st.warning("The CSV has no rows.")
            elif df_up is not None:
                st.caption(f"Loaded {len(df_up)} rows · columns: {', '.join(map(str, df_up.columns))}")
                default_text = next((c for c in TEXT_COLUMNS if c in df_up.columns), df_up.columns[0])
                default_doi = next((c for c in DOI_COLUMNS if c in df_up.columns), None)
                c1, c2 = st.columns([2, 1], gap="large")
                with c1:
                    text_col = st.selectbox("Citation column", list(df_up.columns),
                                            index=list(df_up.columns).index(default_text))
                with c2:
                    use_doi = bool(default_doi) and st.checkbox(f"Use DOI column `{default_doi}`", value=True)
                if len(df_up) > MAX_ROWS:
                    st.warning(f"Only the first {MAX_ROWS} rows will be audited.")
                    df_up = df_up.head(MAX_ROWS)
                if st.button("Run batch audit", type="primary", use_container_width=True):
                    items = [
                        (str(row[text_col]).strip() if pd.notna(row[text_col]) else "",
                         _clean_doi(row[default_doi]) if use_doi else None)
                        for _, row in df_up.iterrows()
                    ]
                    st.session_state["batch_results"] = _run(items)
                    labels = None
                    if "human_label" in df_up.columns:
                        labels = pd.to_numeric(df_up["human_label"], errors="coerce").tolist()
                    st.session_state["batch_labels"] = labels

    with tab_paste:
        pasted = st.text_area(
            "One citation per line (a DOI inside the line is used automatically)", height=200,
            placeholder=("Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. Neural Computation.\n"
                         "Kingma DP, Ba J. Adam: A method for stochastic optimization. arXiv preprint. 2014."),
        )
        if st.button("Audit pasted citations", type="primary", use_container_width=True):
            lines = [line.strip() for line in pasted.splitlines() if line.strip()][:MAX_ROWS]
            if not lines:
                st.warning("Paste at least one citation.")
            else:
                st.session_state["batch_results"] = _run([(line, None) for line in lines])
                st.session_state["batch_labels"] = None

    if "batch_results" not in st.session_state:
        idle_state("No batch yet", "Upload a CSV or paste citations to audit them together.", icon="layers")
        footer("Batch workflow · exportable · reproducible")
        return

    df = st.session_state["batch_results"]
    st.markdown("---")
    st.markdown("### Results")
    n = len(df)
    counts = df["label"].value_counts()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", n)
    for col, lab in zip((m2, m3, m4), ("VERIFIED", "UNCERTAIN", "HALLUCINATED")):
        c = int(counts.get(lab, 0))
        col.metric(lab.title(), f"{c} ({c / n:.0%})")
    errors = int((df["error"] != "").sum())
    if errors:
        st.warning(f"{errors} row(s) could not reach a registry; their verdicts are provisional.")

    left, right = st.columns([1, 2], gap="large")
    with left:
        chart_df = pd.DataFrame({"label": ["VERIFIED", "UNCERTAIN", "HALLUCINATED"],
                                 "count": [int(counts.get(k, 0)) for k in ("VERIFIED", "UNCERTAIN", "HALLUCINATED")]})
        donut = (
            alt.Chart(chart_df).mark_arc(innerRadius=55, outerRadius=100)
            .encode(theta="count:Q",
                    color=alt.Color("label:N", scale=alt.Scale(domain=list(chart_df["label"]),
                                                               range=[TOK["good"], TOK["warn"], TOK["bad"]]),
                                    legend=alt.Legend(orient="bottom", title=None)),
                    tooltip=["label", "count"])
            .properties(height=300, background="transparent")
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(donut, use_container_width=True)
    with right:
        f1, f2 = st.columns(2)
        with f1:
            filt = st.selectbox("Filter", ["All", "VERIFIED", "UNCERTAIN", "HALLUCINATED"])
        with f2:
            ascending = st.checkbox("Lowest score first", value=True)
        view = df if filt == "All" else df[df["label"] == filt]
        view = view.sort_values("score", ascending=ascending)
        cols = ["citation", "label", "score", "reason", "tier", "matched_doi"]
        st.dataframe(view[cols].style.map(style_label_bg, subset=["label"]).map(style_score, subset=["score"])
                     .format({"score": "{:.2f}"}), width="stretch", hide_index=True)

    st.download_button("Download results (CSV)", df.to_csv(index=False).encode("utf-8"),
                       "citeverify_results.csv", "text/csv", use_container_width=True)

    labels = st.session_state.get("batch_labels")
    if labels is not None and len(labels) == n:
        st.markdown("### Evaluation against `human_label`")
        mask = [lab in (0, 1) for lab in labels]
        y_true = [int(lab) for lab, ok in zip(labels, mask) if ok]
        y_pred = [int(lab == "HALLUCINATED") for lab, ok in zip(df["label"], mask) if ok]
        if not y_true:
            st.info("No usable 0/1 labels found.")
        else:
            m = binary_metrics(y_true, y_pred)
            c = m["confusion"]
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Accuracy", f"{m['accuracy']:.1%}")
            k2.metric("Precision", f"{m['precision']:.1%}")
            k3.metric("Recall", f"{m['recall']:.1%}")
            k4.metric("F1", f"{m['f1']:.1%}")
            st.caption(f"Positive class = fabricated; a row counts as flagged when labelled HALLUCINATED. "
                       f"TP {c['tp']} · FP {c['fp']} · FN {c['fn']} · TN {c['tn']} (n = {m['n']}).")

    footer("Batch workflow · exportable · reproducible")
