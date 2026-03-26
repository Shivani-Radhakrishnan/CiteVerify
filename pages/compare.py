"""
Compare Citations Page
"""
import streamlit as st
import pandas as pd
from utils.ui_helpers import hero, verdict_card, feature_badges
from utils.auditor import audit_citation, extract_core_citation
from config import TOK, FEATURE_DESCRIPTIONS, REAL_FEATURES, FAKE_FEATURES


def render():
    """Render the compare page"""
    hero(
        "Compare Citations",
        "Side-by-side comparison of two citations with detailed diff analysis and feature comparison.",
        badges=["A/B testing", "Diff view", "Feature comparison"],
    )

    # Initialize session state
    if "compare_results" not in st.session_state:
        st.session_state["compare_results"] = None

    # Input columns
    col_left, col_right = st.columns(2, gap="large")
    
    with col_left:
        st.markdown("### Citation A")
        citation_a = st.text_area(
            "First citation",
            height=120,
            placeholder="Enter first citation to compare...",
            key="compare_a",
        )
        doi_a = st.text_input("DOI (optional)", key="doi_a")
    
    with col_right:
        st.markdown("### Citation B")
        citation_b = st.text_area(
            "Second citation",
            height=120,
            placeholder="Enter second citation to compare...",
            key="compare_b",
        )
        doi_b = st.text_input("DOI (optional)", key="doi_b")
    
    # Compare button
    if st.button("Compare citations", use_container_width=True):
        if citation_a.strip() and citation_b.strip():
            with st.spinner("Analyzing citations..."):
                result_a = audit_citation(citation_a.strip(), doi_a.strip() or None)
                result_b = audit_citation(citation_b.strip(), doi_b.strip() or None)
                st.session_state["compare_results"] = (result_a, result_b, citation_a, citation_b, doi_a, doi_b)
                st.rerun()
        else:
            st.warning("Please enter both citations to compare.")
    
    # Display comparison results
    if st.session_state["compare_results"]:
        result_a, result_b, citation_a, citation_b, doi_a, doi_b = st.session_state["compare_results"]
        
        st.markdown("---")
        st.markdown("### Comparison Results")
        
        # Metrics comparison
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Citation A Score", f"{result_a.score:.3f}")
        with col2:
            st.metric("Citation B Score", f"{result_b.score:.3f}")
        with col3:
            st.metric("Citation A Label", result_a.label)
        with col4:
            st.metric("Citation B Label", result_b.label)
        
        # Verdict Comparison
        st.markdown("### Verdict Comparison")
        col_a, col_b = st.columns(2, gap="large")
        
        with col_a:
            st.markdown("#### Citation A")
            verdict_card(result_a, show_export=False, citation_text=citation_a, doi_input=doi_a)
        
        with col_b:
            st.markdown("#### Citation B")
            verdict_card(result_b, show_export=False, citation_text=citation_b, doi_input=doi_b)
        
        # Text difference
        with st.expander("Text difference", expanded=True):
            cleaned_a = extract_core_citation(citation_a)
            cleaned_b = extract_core_citation(citation_b)
            
            col_clean_a, col_clean_b = st.columns(2)
            with col_clean_a:
                st.markdown("**Citation A (Cleaned)**")
                st.code(cleaned_a, language="text")
            with col_clean_b:
                st.markdown("**Citation B (Cleaned)**")
                st.code(cleaned_b, language="text")
        
        # Feature comparison
        if hasattr(result_a, 'features') and hasattr(result_b, 'features'):
            with st.expander("Feature comparison", expanded=True):
                features_a = result_a.features or {}
                features_b = result_b.features or {}
                
                # Create comparison data
                comparison_data = []
                for feature in set(list(features_a.keys()) + list(features_b.keys())):
                    val_a = features_a.get(feature, False)
                    val_b = features_b.get(feature, False)
                    
                    desc = FEATURE_DESCRIPTIONS.get(feature, feature)
                    
                    # Determine signal type
                    signal_type = "Real" if feature in REAL_FEATURES else "Fake"
                    
                    comparison_data.append({
                        "Feature": feature.replace("_", " ").title(),
                        "Type": signal_type,
                        "Description": desc,
                        "Citation A": "Yes" if val_a else "—",
                        "Citation B": "Yes" if val_b else "—"
                    })
                
                # Convert to DataFrame and display
                if comparison_data:
                    df_comparison = pd.DataFrame(comparison_data)
                    
                    # Separate real and fake signals
                    real_signals = df_comparison[df_comparison["Type"] == "Real"]
                    fake_signals = df_comparison[df_comparison["Type"] == "Fake"]
                    
                    if not real_signals.empty:
                        st.markdown("#### Real citation signals")
                        st.dataframe(
                            real_signals[["Feature", "Description", "Citation A", "Citation B"]],
                            width='stretch'
                        )
                    
                    if not fake_signals.empty:
                        st.markdown("#### Hallucination signals")
                        st.dataframe(
                            fake_signals[["Feature", "Description", "Citation A", "Citation B"]],
                            width='stretch'
                        )
                    
                    # Summary
                    st.markdown("#### Summary")
                    col_sum1, col_sum2 = st.columns(2)
                    with col_sum1:
                        real_a = len(real_signals[real_signals["Citation A"] == "Yes"])
                        fake_a = len(fake_signals[fake_signals["Citation A"] == "Yes"])
                        st.metric(
                            "Citation A Signals",
                            f"{real_a} real, {fake_a} fake"
                        )
                    with col_sum2:
                        real_b = len(real_signals[real_signals["Citation B"] == "Yes"])
                        fake_b = len(fake_signals[fake_signals["Citation B"] == "Yes"])
                        st.metric(
                            "Citation B Signals",
                            f"{real_b} real, {fake_b} fake"
                        )