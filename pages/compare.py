"""
Compare two citations side by side.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.ui_helpers import comparison_table, evidence_panel, footer, get_auditor, hero, idle_state, verdict_card


def render() -> None:
    hero(
        "Compare Citations",
        "Audit two versions of a reference side by side, e.g. the citation in a draft and the one you "
        "found in the publisher's page.",
        badges=["Side-by-side verdicts", "Check-by-check diff"],
    )

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("### Citation A")
        text_a = st.text_area("First citation", height=120, key="compare_a")
        doi_a = st.text_input("DOI (optional)", key="doi_a")
    with col_b:
        st.markdown("### Citation B")
        text_b = st.text_area("Second citation", height=120, key="compare_b")
        doi_b = st.text_input("DOI (optional)", key="doi_b")

    if st.button("Compare citations", type="primary", use_container_width=True):
        if text_a.strip() and text_b.strip():
            auditor = get_auditor()
            with st.spinner("Checking registries…"):
                pair = auditor.audit_many([(text_a.strip(), doi_a.strip() or None),
                                           (text_b.strip(), doi_b.strip() or None)], max_workers=2)
            st.session_state["compare_results"] = tuple(pair)
        else:
            st.warning("Enter both citations to compare.")

    results = st.session_state.get("compare_results")
    if not results:
        idle_state("Nothing to compare yet", "Enter two citations above and press Compare.", icon="scale")
        footer("Compare · side-by-side audit")
        return

    res_a, res_b = results
    st.markdown("---")
    left, right = st.columns(2, gap="large")
    for col, name, res in ((left, "A", res_a), (right, "B", res_b)):
        with col:
            st.markdown(f"#### Citation {name}")
            verdict_card(res)
            st.dataframe(comparison_table(res), width="stretch", hide_index=True)
            with st.expander("Evidence", expanded=False):
                evidence_panel(res)

    st.markdown("#### Check-by-check")
    names = list(dict.fromkeys([s.name for s in res_a.signals] + [s.name for s in res_b.signals]))
    by_a = {s.name: s.status for s in res_a.signals}
    by_b = {s.name: s.status for s in res_b.signals}
    diff = pd.DataFrame([{"Check": n, "A": by_a.get(n, "—"), "B": by_b.get(n, "—"),
                          "Differs": "yes" if by_a.get(n) != by_b.get(n) else ""} for n in names])
    st.dataframe(diff, width="stretch", hide_index=True)
    footer("Compare · side-by-side audit")
