"""
UI Helper Functions for CiteVerify
"""
import streamlit as st
import pandas as pd
import numpy as np
import hashlib
import base64
from datetime import datetime
from config import TOK, FEATURE_DESCRIPTIONS, REAL_FEATURES, FAKE_FEATURES


# ─────────────────────────────────────────────────────────────────────────────
# Lucide-style inline SVGs (presentation only)
# ─────────────────────────────────────────────────────────────────────────────

_LUCIDE = {
    # Navigation
    "flask-conical": '<svg viewBox="0 0 24 24"><path d="M10 2v6l-5 8a4 4 0 0 0 3.4 6h7.2A4 4 0 0 0 19 16l-5-8V2"/><path d="M8.5 10h7"/></svg>',
    "layers": '<svg viewBox="0 0 24 24"><path d="m12 2 10 6-10 6L2 8z"/><path d="m2 12 10 6 10-6"/><path d="m2 16 10 6 10-6"/></svg>',
    "scale": '<svg viewBox="0 0 24 24"><path d="m12 3 8 4-8 4-8-4z"/><path d="M12 11v10"/><path d="M7 21h10"/><path d="M5 7l-3 6h6z"/><path d="M19 7l-3 6h6z"/></svg>',
    "graduation-cap": '<svg viewBox="0 0 24 24"><path d="m22 10-10 5-10-5 10-5z"/><path d="M6 12v5c0 1 3 3 6 3s6-2 6-3v-5"/><path d="M22 10v6"/></svg>',
    "bar-chart-3": '<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 15v3"/><path d="M12 9v9"/><path d="M17 12v6"/></svg>',
    "book-open": '<svg viewBox="0 0 24 24"><path d="M2 4v16a2 2 0 0 0 2 2h7V6H4a2 2 0 0 0-2 2"/><path d="M22 4v16a2 2 0 0 1-2 2h-7V6h7a2 2 0 0 1 2 2"/></svg>',

    # Pipeline
    "link": '<svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.1 0l2.8-2.8a5 5 0 0 0-7.1-7.1L11.5 4"/><path d="M14 11a5 5 0 0 0-7.1 0L4.1 13.8a5 5 0 0 0 7.1 7.1L12.5 20"/></svg>',
    "calendar": '<svg viewBox="0 0 24 24"><path d="M8 2v4"/><path d="M16 2v4"/><path d="M3 10h18"/><path d="M4 6h16a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2"/></svg>',
    "database": '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg>',
    "sigma": '<svg viewBox="0 0 24 24"><path d="M19 5H7l6 7-6 7h12"/></svg>',

    # Verdict
    "check-circle": '<svg viewBox="0 0 24 24"><path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="M22 4 12 14l-3-3"/></svg>',
    "alert-triangle": '<svg viewBox="0 0 24 24"><path d="m10.3 4.3-8.6 15A2 2 0 0 0 3.4 22h17.2a2 2 0 0 0 1.7-3l-8.6-15a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    "x-circle": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6"/><path d="M9 9l6 6"/></svg>',

    # Actions
    "file-text": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/></svg>',
    "share-2": '<svg viewBox="0 0 24 24"><path d="M18 8a3 3 0 1 0-2.8-4"/><path d="M6 14a3 3 0 1 0 0 6"/><path d="M18 16a3 3 0 1 0 0 6"/><path d="M8.7 13.1l6.6-3.8"/><path d="M8.7 16.9l6.6 3.8"/></svg>',
    "sliders": '<svg viewBox="0 0 24 24"><path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M2 14h4"/><path d="M10 12h4"/><path d="M18 16h4"/></svg>',
    "history": '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/><path d="M12 7v5l4 2"/></svg>',
}


def lucide(name: str) -> str:
    """Return an inline SVG (Lucide-style) for presentation."""
    svg = _LUCIDE.get(name)
    if not svg:
        return '<svg viewBox="0 0 24 24"><path d="M4 12h16"/></svg>'
    return svg


def strip_ui_emoji(text: str) -> str:
    """Remove emoji prefixes used by older UI labels (presentation only)."""
    if not text:
        return text
    # Common prefixes used in this repo
    for p in (
        "🔬 ", "🧪 ", "📦 ", "⚖️ ", "📊 ", "📘 ",
        "✅ ", "⚠️ ", "🚨 ", "🔗 ", "📅 ", "📚 ", "🧮 ",
        "🟢 ", "🔴 ",
    ):
        text = text.replace(p, "")
    return text


def generate_run_id():
    """Generate a unique run ID with timestamp"""
    now = datetime.now()
    return f"CV-{now.strftime('%Y-%m-%d-%H:%M:%S')}"


def generate_config_hash(threshold, model="v1", ruleset="2026-03-01"):
    """Generate a hash of the configuration for reproducibility"""
    config_str = f"{threshold}|{model}|{ruleset}"
    return hashlib.md5(config_str.encode()).hexdigest()[:8]


def create_share_token(run_id):
    """Create a simple share token for results"""
    token = base64.urlsafe_b64encode(run_id.encode()).decode()
    return token[:8]  # Shortened token


def hero(title: str, subtitle: str, badges=None):
    """Render hero section with title, subtitle, and badges"""
    badges = badges or []
    badge_html = "".join([f'<span class="cv-badge">{b}</span>' for b in badges])
    st.markdown(
        f"""
<div style="margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid {TOK['border_soft']};">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
    <div style="min-width:0;">
      <div style="font-size:1.75rem;font-weight:800;letter-spacing:-0.6px;line-height:1.15;color:{TOK['text']};">
        {strip_ui_emoji(title)}
      </div>
      <div style="margin-top:8px;color:{TOK['muted']};font-size:13.5px;max-width:80ch;line-height:1.65;">
        {strip_ui_emoji(subtitle)}
      </div>
    </div>
  </div>
  <div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;">
    {badge_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _label_palette(label: str):
    """Get color palette for a label"""
    if label == "VERIFIED":
        return TOK["good"], "rgba(34,197,94,0.12)", "rgba(34,197,94,0.35)"
    if label == "UNCERTAIN":
        return TOK["warn"], "rgba(245,158,11,0.12)", "rgba(245,158,11,0.35)"
    return TOK["bad"], "rgba(239,68,68,0.12)", "rgba(239,68,68,0.35)"


def _tier_num(tier_text: str) -> str:
    """Extract tier number from tier text"""
    t = (tier_text or "").lower()
    if "doi registry" in t or "datacite" in t or "crossref" in t:
        return "01"
    if "temporal" in t:
        return "02"
    if "known papers" in t or "database" in t:
        return "03"
    if "plausibility" in t or "regex" in t:
        return "04"
    return "—"


def tier_stepper(active_tier: str):
    """Render tier stepper visualization"""
    num = _tier_num(active_tier)
    steps = [
        ("01", "link", "DOI Registry"),
        ("02", "calendar", "Temporal"),
        ("03", "database", "Known DB"),
        ("04", "sigma", "Plausibility"),
    ]
    parts = []
    for i, (n, icon, name) in enumerate(steps):
        order = int(n)
        active_order = int(num) if num.isdigit() else 99
        if order < active_order:
            cls = "done"
            dot = "✓"
        elif order == active_order:
            cls = "active"
            dot = "●"
        else:
            cls = "idle"
            dot = str(order)

        parts.append(
            f'<div class="cv-step {cls}">'
            f'<span style="font-weight:800;">{dot}</span>'
            f'<span style="display:inline-flex;align-items:center;gap:8px;">'
            f'<span class="cv-ico">{lucide(icon)}</span>'
            f'<span>{name}</span>'
            f'</span>'
            f'</div>'
        )
        if i < len(steps) - 1:
            connector_cls = "done" if order < active_order else ""
            parts.append(f'<div class="cv-step-connector {connector_cls}"></div>')

    st.markdown(
        f'<div class="cv-pipeline">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


def verdict_card(result, show_export=True, citation_text="", doi_input=""):
    """Render verdict card for audit result with proper styling"""
    color, bg, border_col = _label_palette(result.label)
    score_pct = int(round(result.score * 100))

    label_map = {
        "VERIFIED": ("VERIFIED", TOK["good"], "check-circle"),
        "UNCERTAIN": ("UNCERTAIN", TOK["warn"], "alert-triangle"),
        "HALLUCINATED": ("HALLUCINATED", TOK["bad"], "x-circle"),
    }
    label_text, label_color, label_icon = label_map.get(result.label, (strip_ui_emoji(result.label), color, "alert-triangle"))

    tier_display = _tier_num(result.tier)

    # Generate run ID and config hash if not exists
    if "run_id" not in st.session_state:
        st.session_state["run_id"] = generate_run_id()
        st.session_state["config_hash"] = generate_config_hash(st.session_state.get("threshold", 0.20))

    # Use a container with custom HTML for proper styling
    verdict_display = strip_ui_emoji(getattr(result, "verdict", ""))
    sub_display = strip_ui_emoji(getattr(result, "sub", ""))

    import streamlit.components.v1 as components

    html = f"""

<div class="cv-verdict-card" style="
  border-color: {border_col};
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  margin-bottom: 16px;
">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
    <div style="flex:1;min-width:0;">
      <div style="display:inline-flex;align-items:center;gap:10px;
        border-radius:999px;padding:6px 12px;
        background:{bg};border:1px solid {border_col};margin-bottom:12px;">
        <span class="cv-ico" style="color:{label_color};">{lucide(label_icon)}</span>
        <span style="font-weight:800;font-size:13px;letter-spacing:0.02em;color:{label_color};">{label_text}</span>
        <span style="width:6px;height:6px;border-radius:50%;background:{color};margin-left:2px;"></span>
      </div>

      <div style="font-size:1.05rem;font-weight:750;margin-bottom:6px;color:{TOK['text']};">
        {verdict_display}
      </div>
      <div style="color:{TOK['muted']};font-family:{TOK['mono']};font-size:12px;margin-bottom:12px;">
        {sub_display} &nbsp;·&nbsp; Tier {tier_display}
      </div>

      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <span class="cv-badge">{st.session_state.get('run_id', '')[:24]}</span>
        <span class="cv-badge">Config {st.session_state.get('config_hash', '')}</span>
      </div>
    </div>

    <div style="text-align:right;min-width:150px;flex-shrink:0;">
      <div style="font-family:{TOK['mono']};font-size:11px;color:{TOK['muted']};
        text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Plausibility</div>
      <div style="font-family:{TOK['mono']};font-weight:900;font-size:2.1rem;
        color:{color};line-height:1;letter-spacing:-0.8px;">{result.score:.2f}</div>
      <div style="font-family:{TOK['mono']};font-size:11px;color:{TOK['muted']};margin-top:6px;">{score_pct}%</div>
    </div>
  </div>

  <div class="cv-progress-bar">
    <div style="width:{score_pct}%;height:100%;background:{color};border-radius:999px;transition:width 0.45s ease;"></div>
  </div>

  <div style="display:grid;grid-template-columns:1.25fr 0.95fr;gap:12px;margin-top:16px;">
    <div style="background:rgba(15,23,42,0.02);border:1px solid {TOK['border_soft']};border-radius:14px;padding:14px;">
      <div style="font-size:10px;color:{TOK['muted']};font-family:{TOK['mono']};
        text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;">Interpretation</div>
      <div style="color:{TOK['subtext']};line-height:1.7;font-size:13.5px;">{strip_ui_emoji(result.explanation)}</div>
    </div>
    <div style="background:{bg};border:1px solid {border_col};border-radius:14px;padding:14px;">
      <div style="font-size:10px;color:{TOK['muted']};font-family:{TOK['mono']};
        text-transform:uppercase;letter-spacing:1.2px;margin-bottom:8px;">Recommended action</div>
      <div style="font-weight:700;color:{TOK['text']};line-height:1.6;font-size:13.5px;">{strip_ui_emoji(result.action)}</div>
    </div>
  </div>
</div>

"""

    # Render via components.html to avoid raw HTML appearing as text
    base_h = 260
    extra = 0
    try:
        if len(verdict_display) > 140:
            extra += 40
        if len(sub_display) > 180:
            extra += 40
    except Exception:
        pass
    components.html(html, height=base_h + extra, scrolling=False)

    
    # Export buttons (outside the main card)
    if show_export:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export PDF", key=f"pdf_{id(result)}", use_container_width=True):
                from utils.pdf_generator import generate_pdf_report
                pdf_buffer = generate_pdf_report(
                    result, citation_text, doi_input,
                    st.session_state.get("run_id", ""),
                    st.session_state.get("config_hash", "")
                )
                st.download_button(
                    label="Download PDF",
                    data=pdf_buffer.getvalue(),
                    file_name=f"citeverify_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )
        
        with col2:
            if st.button("Copy share token", key=f"share_{id(result)}", use_container_width=True):
                token = create_share_token(st.session_state.get('run_id', ''))
                st.success(f"Share token copied: {token}")


def evidence_panel(result):
    """Display evidence with strength tags"""
    if not hasattr(result, 'features') or not result.features:
        return
    
    # Define evidence items with strength
    evidence_items = []
    
    # Strong evidence
    if result.features.get("doi_valid"):
        evidence_items.append(("DOI resolves via registry", "Strong", True))
    if result.features.get("year_valid"):
        evidence_items.append(("Year is within valid range", "Strong", True))
    
    # Moderate evidence
    if result.features.get("ends_connective"):
        evidence_items.append(("Citation ends with connective", "Moderate", True))
    if result.features.get("starts_context"):
        evidence_items.append(("Citation starts with context marker", "Moderate", True))
    if result.features.get("title_phrase"):
        evidence_items.append(("Title phrase pattern detected", "Moderate", False))
    if result.features.get("ends_venue"):
        evidence_items.append(("Citation ends with venue name", "Moderate", False))
    
    # Weak evidence
    if result.features.get("short_fragment"):
        evidence_items.append(("Short author-year fragment", "Weak", True))
    if result.features.get("many_initials"):
        evidence_items.append(("Many initial-style authors", "Weak", False))
    if result.features.get("long_entry"):
        evidence_items.append(("Long entry (10+ words)", "Weak", False))
    
    # Display evidence
    for text, strength, positive in evidence_items:
        color = TOK["good"] if positive else TOK["bad"]
        strength_color = TOK["good"] if strength == "Strong" else TOK["warn"] if strength == "Moderate" else TOK["muted"]
        
        st.markdown(
            f"""
<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;
  background:rgba(8,14,28,0.4);border:1px solid {TOK['border']};border-radius:10px;margin-bottom:8px;">
  <span style="font-family:{TOK['mono']};font-size:11px;font-weight:800;
    color:{strength_color};min-width:70px;">{strength}</span>
  <div style="flex:1;">
    <div style="font-weight:700;color:{TOK['text']};">{text}</div>
  </div>
  <span style="color:{color};font-weight:800;">{'✓' if positive else '×'}</span>
</div>
""",
            unsafe_allow_html=True,
        )
import re
import streamlit as st
from config import TOK

def evidence_panel_safe(result, raw_text: str):
    """
    Presentation-layer only.
    If the backend didn't provide evidence/features (common on early-exit tiers),
    render a minimal, honest explanation based on tier + simple surface checks.
    """
    # 1) If the existing evidence panel has something meaningful, use it
    feats = getattr(result, "features", None)
    ev = getattr(result, "evidence", None)

    if feats or ev:
        # your original renderer
        return evidence_panel(result)

    # 2) Fallback evidence (no backend changes)
    st.markdown("**Why this was flagged**")

    reasons = []

    # Temporal sanity check fallback
    if "Temporal" in (result.tier or ""):
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", raw_text or "")
        bad_years = []
        for y in years:
            try:
                if int(y) > 2025:   # keep consistent with your dataset logic
                    bad_years.append(y)
            except:
                pass
        if bad_years:
            reasons.append(("Future year detected", f"Found year(s): {', '.join(sorted(set(bad_years)))}"))
        else:
            reasons.append(("Temporal inconsistency", "Year formatting or range appeared invalid."))

    # DOI registry fallback
    if "DOI" in (result.tier or ""):
        reasons.append(("DOI registry check", "The DOI could not be verified in the selected registries."))

    # Known DB fallback
    if "Known" in (result.tier or ""):
        reasons.append(("Known database", "No match found in the curated known-papers list."))

    if not reasons:
        reasons.append(("Evidence unavailable", "This tier returned no structured evidence fields."))

    # Render as clean cards
    for title, desc in reasons:
        st.markdown(
            f"""
<div class="cv-softnote" style="margin-top:10px;">
  <div style="font-weight:700;color:{TOK['text']};margin-bottom:4px;">{title}</div>
  <div style="color:{TOK['muted']};">{desc}</div>
</div>
""",
            unsafe_allow_html=True
        )

def feature_badges(features: dict):
    """Two-column feature grid: Real signals vs Fake signals."""
    if not features:
        st.info("No features extracted.")
        return

    real_defs = [
        ("ends_connective", "Ends with connective", "Inline fragment / mid-sentence"),
        ("starts_context",  "Starts with context marker", "Inline mention pattern"),
        ("multi_inline",    "Multiple author–year pairs", "Inline style"),
        ("year_suffix",     "Year suffix a/b", "Disambiguation (2023a)"),
        ("short_fragment",  "Short author–year fragment", "≤ 12 words"),
    ]
    fake_defs = [
        ("initial_author",  "Surname + initial pattern", "Reference-list format"),
        ("title_phrase",    "Long title phrase after year", "Reference entry signal"),
        ("ends_venue",      "Ends with venue name", "ACL / NeurIPS / etc."),
        ("many_initials",   "Many initial-style authors", "Reference list format"),
        ("long_entry",      "Long entry (10+ words)", "Reference list length"),
        ("year_first",      "Starts with year", "Author missing / cutoff"),
    ]

    def chip(key, title, desc, is_real):
        active = bool(features.get(key))
        if is_real:
            c = TOK["good"]; glow = "rgba(34,197,94,0.14)"; border = "rgba(34,197,94,0.3)"
        else:
            c = TOK["bad"];  glow = "rgba(239,68,68,0.14)"; border = "rgba(239,68,68,0.3)"

        if active:
            bg = glow; bc = border; op = "1"
        else:
            bg = "rgba(8,14,28,0.3)"; bc = TOK["border"]; op = "0.5"

        check = "✓" if active else "—"
        return f"""
        <div class="cv-feat-chip" style="background:{bg};border-color:{bc};opacity:{op};">
          <span style="font-weight:900;color:{c};min-width:14px;">{check}</span>
          <div>
            <div style="font-weight:700;color:{TOK['text']};font-size:12px;">{title}</div>
            <div style="color:{TOK['muted']};font-size:11px;margin-top:1px;">{desc}</div>
          </div>
        </div>
        """

    real_chips = "".join([chip(k, t, d, True) for k, t, d in real_defs])
    fake_chips = "".join([chip(k, t, d, False) for k, t, d in fake_defs])

    st.markdown(
        f"""
<div class="cv-feat-grid">
  <div class="cv-feat-col">
    <div style="font-size:11px;font-family:{TOK['mono']};font-weight:800;
      color:{TOK['good']};text-transform:uppercase;letter-spacing:1.2px;
      padding:6px 10px;background:rgba(34,197,94,0.08);border-radius:6px;
      border:1px solid rgba(34,197,94,0.2);margin-bottom:4px;">
      Real signals
    </div>
    {real_chips}
  </div>
  <div class="cv-feat-col">
    <div style="font-size:11px;font-family:{TOK['mono']};font-weight:800;
      color:{TOK['bad']};text-transform:uppercase;letter-spacing:1.2px;
      padding:6px 10px;background:rgba(239,68,68,0.08);border-radius:6px;
      border:1px solid rgba(239,68,68,0.2);margin-bottom:4px;">
      Fake signals
    </div>
    {fake_chips}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def style_label_bg(v: str) -> str:
    """Style function for label background in dataframes"""
    if v == "VERIFIED":
        return "background-color:rgba(34,197,94,0.12); color:#86efac; font-weight:700"
    if v == "UNCERTAIN":
        return "background-color:rgba(245,158,11,0.12); color:#fcd34d; font-weight:700"
    return "background-color:rgba(239,68,68,0.12); color:#fca5a5; font-weight:700"


def style_score(v) -> str:
    """Style function for score in dataframes"""
    try:
        x = float(v)
        if x >= 0.7:  return "color:#86efac; font-weight:700"
        if x >= 0.4:  return "color:#fcd34d; font-weight:650"
        return "color:#fca5a5; font-weight:650"
    except Exception:
        return ""


def render_sidebar():
    """Render the sidebar with navigation and settings"""
    # Logo / brand
    st.markdown(
        f"""
<div style="padding:22px 14px 16px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
    <div style="width:34px;height:34px;border-radius:12px;background:{TOK['accent']};
      display:flex;align-items:center;justify-content:center;color:white;font-weight:900;
      letter-spacing:-0.5px;">CV</div>
    <div style="min-width:0;">
      <div style="font-size:1.18rem;font-weight:800;letter-spacing:-0.4px;color:{TOK['text']};">
        CiteVerify
      </div>
      <div style="font-size:11.5px;color:{TOK['muted']};font-family:{TOK['mono']};letter-spacing:0.2px;">
        Citation hallucination detection
      </div>
    </div>
  </div>
</div>
<div style="height:1px;background:{TOK['border_soft']};margin:0 14px 14px;"></div>
""",
        unsafe_allow_html=True,
    )

    # Navigation
    st.markdown(
        f'<div style="font-size:10.5px;color:{TOK["muted"]};font-family:{TOK["mono"]};'
        f'text-transform:uppercase;letter-spacing:1.2px;padding:0 14px 8px;">Navigation</div>',
        unsafe_allow_html=True,
    )
    
    # Navigation (single, non-duplicated)
    # We render a compact icon + button row per item.
    from config import NAV_ITEMS
    for icon_name, label, key in NAV_ITEMS:
        active = st.session_state.get("page") == key
        ico_col, btn_col = st.columns([0.16, 0.84], gap="small")
        with ico_col:
            st.markdown(
                f'<div style="margin-top:2px;display:flex;justify-content:center;">'
                f'<span class="cv-ico" style="color:{TOK["accent"]};opacity:{1.0 if active else 0.72};">{lucide(icon_name)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button(
                label,
                key=f"navbtn_{key}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state["page"] = key
                st.rerun()

    st.markdown(
        f'<div style="height:1px;background:{TOK["border_soft"]};margin:14px 14px;"></div>',
        unsafe_allow_html=True,
    )

    # Settings
    st.markdown(
        f'<div style="font-size:10.5px;color:{TOK["muted"]};font-family:{TOK["mono"]};'
        f'text-transform:uppercase;letter-spacing:1.2px;padding:0 14px 10px;">Audit settings</div>',
        unsafe_allow_html=True,
    )
    threshold = st.slider(
        "Plausibility threshold",
        0.10, 0.60, 0.20, 0.05,
        help="Scores below this are flagged as hallucinations (batch eval vs ground truth).",
    )
    st.session_state["threshold"] = threshold
    show_features = st.checkbox("Show feature breakdown", value=True)
    show_compare  = st.checkbox("Show cleaned vs original", value=True)
    auto_demo     = st.toggle("Auto-run examples", value=True, help="Auto-run when selecting a quick example.")

    # Keyboard shortcuts info
    st.markdown(
        f'<div style="font-size:10.5px;color:{TOK["muted"]};font-family:{TOK["mono"]};'
        f'text-transform:uppercase;letter-spacing:1.2px;padding:0 14px 10px;margin-top:20px;">Shortcuts</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div style="padding:0 14px;font-size:12px;color:{TOK['subtext']};line-height:1.8;">
  <div style="margin-bottom:8px;"><span class="cv-kbd">Enter</span> Run audit</div>
  <div style="margin-bottom:8px;"><span class="cv-kbd">Ctrl+K</span> Command palette</div>
  <div style="margin-bottom:8px;"><span class="cv-kbd">/</span> Focus search</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="height:1px;background:{TOK["border_soft"]};margin:14px 14px;"></div>',
        unsafe_allow_html=True,
    )

    # Pipeline info
    st.markdown(
        f"""
<div style="padding:0 14px 14px;">
  <div style="font-size:10.5px;color:{TOK['muted']};font-family:{TOK['mono']};
    text-transform:uppercase;letter-spacing:1.2px;margin-bottom:10px;">Detection pipeline</div>
  {"".join([
      f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">'
      f'<div style="width:20px;height:20px;border-radius:6px;background:rgba(36,59,107,0.08);'
      f'border:1px solid rgba(36,59,107,0.18);display:flex;align-items:center;justify-content:center;'
      f'font-family:{TOK["mono"]};font-size:10px;font-weight:800;color:{TOK["accent"]};flex-shrink:0;">{n}</div>'
      f'<div style="font-family:{TOK["mono"]};font-size:11.5px;color:{TOK["subtext"]};">{label}</div>'
      f'</div>'
      for n, label in [("01","DOI Registry"), ("02","Temporal Check"), ("03","Known DB"), ("04","Plausibility")]
  ])}
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div style="padding:12px 14px;background:rgba(15,23,42,0.02);border-top:1px solid {TOK['border_soft']};">
  <div style="font-family:{TOK['mono']};font-size:10.5px;color:{TOK['muted']};">CiteVerify · research UI</div>
</div>
""",
        unsafe_allow_html=True,
    )
    
    return threshold, show_features, show_compare, auto_demo