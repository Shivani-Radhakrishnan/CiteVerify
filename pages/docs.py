"""
Documentation Page
"""
import streamlit as st
from utils.ui_helpers import hero, lucide, strip_ui_emoji
from config import TOK


def render():
    """Render the documentation page"""
    hero(
        "How CiteVerify Works",
        "A transparent, tiered pipeline. Designed for explainability and reproducibility in research demos.",
        badges=["4-tier design", "Registry-aware DOI routing", "Interpretable scoring"],
    )

    tiers = [
        ("01", "link", "DOI Registry Verification",
         "If a DOI is provided, CiteVerify routes to the correct registry. arXiv-assigned DOIs (10.48550/arXiv.*) are registered via DataCite (not Crossref), so Crossref may return 'not found' even when the DOI is valid. CiteVerify queries the appropriate registry and can cross-check via arXiv when relevant."),
        ("02", "calendar", "Temporal Sanity Check",
         "Extracts 4-digit years from the citation string and flags values that are implausible for academic publishing (too old or too far in the future)."),
        ("03", "database", "Known Papers Database",
         "Fast path for known-real and known-fake citations from the study set. When matched, the scorer is bypassed for maximum confidence."),
        ("04", "sigma", "Plausibility Scoring (features)",
         "For all remaining cases, the engine extracts interpretable patterns and computes a bounded plausibility score. Inline mention signals increase the score; reference-entry signals decrease it."),
    ]

    for n, icon, name, desc in tiers:
        # Default collapsed so page doesn't dump a wall of text
        with st.expander(f"**Tier {n}** — {name}", expanded=False):
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;color:{TOK["accent"]};">'
                f'<span class="cv-ico">{lucide(icon)}</span>'
                f'<span style="font-family:{TOK["mono"]};font-size:12px;letter-spacing:0.02em;">Pipeline tier</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(desc)

    st.markdown("---")
    st.markdown("### Score interpretation")

    score_rows = [
        ("≥ 0.70",     "VERIFIED",   TOK["good"], "Strong inline-fragment signals"),
        ("0.50–0.69",  "LIKELY REAL", TOK["warn"], "Moderate signals"),
        ("0.20–0.49",  "UNCERTAIN",  TOK["warn"], "Mixed / weak signals — manual review"),
        ("< 0.20",     "HALLUCINATED", TOK["bad"],  "Strong fake signals — remove / replace"),
    ]

    for rng, label, color, note in score_rows:
        st.markdown(
            f"""
<div style="display:flex;align-items:center;gap:14px;padding:12px 16px;
  background:{TOK['card']};border:1px solid {TOK['border']};border-radius:12px;margin-bottom:8px;">
  <div style="font-family:{TOK['mono']};font-size:13px;font-weight:800;
    color:{color};min-width:80px;">{rng}</div>
  <div style="font-weight:750;color:{TOK['text']};min-width:160px;letter-spacing:0.02em;">{label}</div>
  <div style="color:{TOK['muted']};font-size:13px;">{note}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Feature Signal Guide")

    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### Real citation signals")
        real_signals = [
            ("Ends with connective", "Citation ends with words like 'and', 'or', 'in', 'the' - typical of inline mentions"),
            ("Starts with context marker", "Begins with 'as shown by', 'according to' - inline citation pattern"),
            ("Multiple author-year pairs", "Contains multiple (Author, Year) patterns - inline style"),
            ("Year suffix", "Uses 2023a/2023b disambiguation - academic convention"),
            ("Short fragment", "Brief author-year format (≤12 words) - typical inline citation"),
        ]
        
        for signal, desc in real_signals:
            st.markdown(
                f"""
<div style="padding:10px 12px;margin-bottom:8px;border-left:3px solid {TOK['good']};background:rgba(15,122,74,0.06);border-radius:10px;border:1px solid {TOK['border_soft']};">
  <div style="font-weight:700;color:{TOK['text']};font-size:13px;">{signal}</div>
  <div style="color:{TOK['subtext']};font-size:12px;margin-top:2px;">{desc}</div>
</div>
""",
                unsafe_allow_html=True,
            )
    
    with col2:
        st.markdown("#### Hallucination signals")
        fake_signals = [
            ("Surname + initial pattern", "Author names as 'Smith J.' - reference list format"),
            ("Title phrase after year", "Long title following year - reference entry style"),
            ("Ends with venue name", "Ends with conference/journal name - reference entry"),
            ("Many initial-style authors", "Multiple 'A. B. C.' patterns - reference list"),
            ("Long entry", "10+ words - typical of full reference entries"),
            ("Starts with year", "Year appears first without author - suspicious pattern"),
        ]
        
        for signal, desc in fake_signals:
            st.markdown(
                f"""
<div style="padding:10px 12px;margin-bottom:8px;border-left:3px solid {TOK['bad']};background:rgba(180,35,24,0.06);border-radius:10px;border:1px solid {TOK['border_soft']};">
  <div style="font-weight:700;color:{TOK['text']};font-size:13px;">{signal}</div>
  <div style="color:{TOK['subtext']};font-size:12px;margin-top:2px;">{desc}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("### Known limitations")
    for limitation in [
        "Plausibility tier is heuristic — provide a DOI for high-stakes verification.",
        "Truncated citations can hide author/year, affecting classification.",
        "arXiv-like IDs may require external scholarly lookup for maximal confidence.",
        "The system may not detect all types of hallucinated citations.",
        "Citations that closely resemble real papers may be misclassified.",
    ]:
        st.markdown(
            f"""
<div style="display:flex;gap:10px;padding:10px 14px;margin-bottom:6px;
  background:{TOK['card']};border:1px solid {TOK['border']};border-radius:12px;">
  <span style="color:{TOK['warn']};" class="cv-ico">{lucide('alert-triangle')}</span>
  <span style="color:{TOK['subtext']};font-size:13.5px;">{limitation}</span>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### API Usage")

    st.markdown("""
    **Programmatic Access**
    
    You can use CiteVerify programmatically:
    
    ```python
    from utils.auditor import audit_citation
    
    # Simple audit
    result = audit_citation("vaswani a 2017 attention is all you need")
    print(f"Score: {result.score}")
    print(f"Label: {result.label}")
    print(f"Verdict: {result.verdict}")
    
    # With DOI verification
    result = audit_citation(
        "vaswani a 2017 attention is all you need",
        doi="10.48550/arXiv.1706.03762"
    )
    ```
    """)

    st.markdown("---")
    st.markdown("### Version History")

    version_history = [
        ("v1.0", "2026-03-03", [
            "Initial release with 4-tier detection pipeline",
            "DOI registry verification (Crossref, DataCite, arXiv)",
            "Batch audit with error analysis lab",
            "Study mode with ground truth evaluation",
            "PDF export and shareable results",
            "Compare mode for A/B testing"
        ]),
    ]

    for version, date, features in version_history:
        with st.expander(f"**{version}** — {date}", expanded=(version == "v1.0")):
            for feature in features:
                st.markdown(f"• {feature}")

    st.markdown("---")
    st.markdown("### Citation")
    
    st.markdown("""
    If you use CiteVerify in your research, please cite:
    
    ```bibtex
    @software{citeverify2026,
      title={CiteVerify: Citation Hallucination Detection},
      author={CiteVerify Team},
      year={2026},
      url={https://github.com/your-repo/citeverify}
    }
    ```
    """)

    st.markdown(
        f"""
<hr>
<div style="text-align:center;color:{TOK['muted']};font-family:{TOK['mono']};font-size:11px;">
  Documentation · transparent methodology
</div>
""",
        unsafe_allow_html=True,
    )