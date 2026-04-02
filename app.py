"""
CiteVerify — Citation Hallucination Detection
Streamlit app. Run: streamlit run app.py
"""
import sys
import warnings
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
from PIL import Image

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add utils to path
sys.path.insert(0, ".")
from utils.auditor import audit_citation, AuditResult, extract_core_citation
from utils.ui_helpers import render_sidebar, hero
from config import TOK, NAV_ITEMS, CSS_STYLES

# Import all page modules
from pages.single_audit import render as render_single_audit
from pages.compare import render as render_compare
from pages.batch_audit import render as render_batch_audit
from pages.study_mode import render as render_study_mode
from pages.analytics import render as render_analytics
from pages.docs import render as render_docs

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CiteVerify — Citation Audit",
    page_icon=Image.open("assets/icon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# Apply CSS styles
# ──────────────────────────────────────────────────────────────────────────────

st.markdown(CSS_STYLES, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Initialize session state
# ──────────────────────────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state["page"] = NAV_ITEMS[0][2]

# ──────────────────────────────────────────────────────────────────────────────
# Render sidebar
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    threshold, show_features, show_compare, auto_demo = render_sidebar()

# ──────────────────────────────────────────────────────────────────────────────
# Route to appropriate page
# ──────────────────────────────────────────────────────────────────────────────

page = st.session_state["page"]

try:
    if page == "single":
        render_single_audit()
    elif page == "compare":
        render_compare()
    elif page == "batch":
        render_batch_audit()
    elif page == "study":
        render_study_mode()
    elif page == "analytics":
        render_analytics()
    elif page == "docs":
        render_docs()
    else:
        st.error(f"Unknown page: {page}")
        st.info("Please select a page from the navigation sidebar.")
except Exception as e:
    st.error(f"Error loading page: {str(e)}")
    st.markdown("### Debug Information")
    st.code(f"Page: {page}\nError: {str(e)}", language="python")
