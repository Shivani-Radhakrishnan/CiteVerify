"""
CiteVerify — Citation Hallucination Detection
Streamlit app. Run: streamlit run app.py
"""
from pathlib import Path

import streamlit as st
from PIL import Image

from config import CSS_STYLES, NAV_ITEMS
from pages.analytics import render as render_analytics
from pages.batch_audit import render as render_batch_audit
from pages.compare import render as render_compare
from pages.docs import render as render_docs
from pages.single_audit import render as render_single_audit
from pages.study_mode import render as render_study_mode
from utils.ui_helpers import render_sidebar

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="CiteVerify — Citation Audit",
    page_icon=Image.open(ROOT / "assets" / "icon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS_STYLES, unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state["page"] = NAV_ITEMS[0][2]

with st.sidebar:
    render_sidebar()

PAGES = {
    "single": render_single_audit,
    "batch": render_batch_audit,
    "compare": render_compare,
    "study": render_study_mode,
    "analytics": render_analytics,
    "docs": render_docs,
}

page = st.session_state["page"]
render = PAGES.get(page)
if render is None:
    st.error(f"Unknown page: {page}")
else:
    try:
        render()
    except Exception as exc:  # keep the app usable; details are in an expander, not a raw traceback
        st.error(f"Something went wrong while rendering this page: {exc}")
        with st.expander("Details"):
            st.exception(exc)
