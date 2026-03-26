"""
CiteVerify Configuration

This module is **presentation-layer only**.

Non-negotiable: do not change any detection logic, scoring, routing, API behavior,
registry behavior, or backend architecture. Only UI tokens and styling live here.
"""

# Design tokens (Swiss / International + luxury minimal + corporate professional)
TOK = {
    # Base
    "bg": "#F7F8FA",
    "panel": "#FFFFFF",
    "card": "#FFFFFF",
    "border": "#D9DEE6",
    "border_soft": "#E8ECF2",

    # Text
    "text": "#0F172A",
    "subtext": "#334155",
    "muted": "#5B6676",

    # Semantic (strict usage)
    "good": "#0F7A4A",  # VERIFIED
    "warn": "#B45309",  # UNCERTAIN
    "bad": "#B42318",   # HALLUCINATED

    # Accent (single cohesive accent)
    "accent": "#243B6B",  # restrained navy / slate

    # Typography
    "mono": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
    "sans": "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",

    # Spacing grid
    "grid": 8,
}

# Navigation items (Lucide icon name, label, route key)
NAV_ITEMS = [
    ("flask-conical", "Single audit", "single"),
    ("layers", "Batch audit", "batch"),
    ("scale", "Compare", "compare"),
    ("graduation-cap", "Study mode", "study"),
    ("bar-chart-3", "Analytics", "analytics"),
    ("book-open", "Documentation", "docs"),
]

# Feature descriptions
FEATURE_DESCRIPTIONS = {
    "doi_valid": "DOI resolves correctly",
    "year_valid": "Year is within valid range",
    "title_phrase": "Contains title phrase pattern",
    "ends_venue": "Ends with venue name",
    "ends_connective": "Ends with connective word",
    "starts_context": "Starts with context marker",
    "short_fragment": "Short author-year fragment",
    "many_initials": "Many initial-style authors",
    "long_entry": "Long entry (10+ words)",
    "year_first": "Starts with year",
    "initial_author": "Surname + initial pattern",
    "multi_inline": "Multiple author-year pairs",
    "year_suffix": "Year suffix (a/b)",
}

# Real vs fake signal classification
REAL_FEATURES = [
    "doi_valid",
    "year_valid",
    "ends_connective",
    "starts_context",
    "short_fragment",
    "multi_inline",
    "year_suffix",
]
FAKE_FEATURES = [
    "title_phrase",
    "ends_venue",
    "many_initials",
    "long_entry",
    "year_first",
    "initial_author",
]

# Complete CSS styles (IMPORTANT: all CSS braces must be doubled inside f-strings)
CSS_STYLES = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --cv-grid: {TOK['grid']}px;
  --cv-bg: {TOK['bg']};
  --cv-panel: {TOK['panel']};
  --cv-card: {TOK['card']};
  --cv-border: {TOK['border']};
  --cv-border-soft: {TOK['border_soft']};
  --cv-text: {TOK['text']};
  --cv-subtext: {TOK['subtext']};
  --cv-muted: {TOK['muted']};
  --cv-accent: {TOK['accent']};
  --cv-good: {TOK['good']};
  --cv-warn: {TOK['warn']};
  --cv-bad: {TOK['bad']};
}}

html, body, [data-testid="stAppViewContainer"] {{
  background: var(--cv-bg) !important;
  color: var(--cv-text) !important;
  font-family: {TOK['sans']} !important;
}}

/* ─────────────────────────────────────────────────────────────
   MAIN LAYOUT
   Fix: top line being hidden under Streamlit chrome
   ───────────────────────────────────────────────────────────── */
section.main .block-container {{
  padding-top: calc(var(--cv-grid) * 5) !important;    /* 40px */
  padding-bottom: calc(var(--cv-grid) * 4) !important;/* 32px */
  padding-left: calc(var(--cv-grid) * 4) !important;   /* 32px */
  padding-right: calc(var(--cv-grid) * 4) !important;  /* 32px */
  max-width: 1480px !important;
}}

[data-testid="stHorizontalBlock"] {{
  gap: calc(var(--cv-grid) * 2) !important; /* 16px */
}}

@media (max-width: 1100px) {{
  section.main .block-container {{
    padding-left: calc(var(--cv-grid) * 2) !important;
    padding-right: calc(var(--cv-grid) * 2) !important;
    max-width: 100% !important;
  }}
  [data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap !important;
  }}
  [data-testid="column"] {{
    min-width: 340px !important;
    flex: 1 1 340px !important;
  }}
}}
@media (max-width: 520px) {{
  [data-testid="column"] {{ min-width: 0 !important; }}
}}

/* ─────────────────────────────────────────────────────────────
   SIDEBAR
   Fix: cramped + content starting mid sidebar
   ───────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
  background: var(--cv-panel) !important;
  border-right: 1px solid var(--cv-border) !important;
}}

section[data-testid="stSidebar"] .block-container {{
  padding-top: 18px !important;
  padding-bottom: 16px !important;
  padding-left: 16px !important;
  padding-right: 16px !important;
  margin: 0 !important;
  max-height: 100vh !important;
  overflow-y: auto !important;
}}

section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
  gap: 12px !important;
  margin: 0 !important;
  padding: 0 !important;
}}

[data-testid="stSidebarNav"],
[data-testid="stSidebarNavSeparator"] {{
  display: none !important;
}}

/* Typography */
h1, h2, h3, h4 {{
  font-family: {TOK['sans']} !important;
  color: var(--cv-text) !important;
  letter-spacing: -0.3px;
}}
p, label, li {{ color: var(--cv-subtext) !important; }}
small {{ color: var(--cv-muted) !important; }}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
  background: var(--cv-panel) !important;
  border: 1px solid var(--cv-border) !important;
  color: var(--cv-text) !important;
  border-radius: 12px !important;
  font-family: {TOK['mono']} !important;
  font-size: 13px !important;
  line-height: 1.65 !important;
  transition: border-color 0.18s, box-shadow 0.18s !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
  border-color: rgba(36,59,107,0.55) !important;
  box-shadow: 0 0 0 3px rgba(36,59,107,0.12) !important;
  outline: none !important;
}}

/* Buttons */
.stButton > button {{
  background: var(--cv-accent) !important;
  color: white !important;
  border: 1px solid rgba(0,0,0,0) !important;
  border-radius: 12px !important;
  font-family: {TOK['sans']} !important;
  font-weight: 700 !important;
  padding: 0.6rem 1rem !important;
  transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease !important;
  letter-spacing: 0.01em !important;
}}
.stButton > button p,
.stButton > button span {{ color: inherit !important; }}

.stButton > button[kind="secondary"],
.stButton > button[kind="secondaryFormSubmit"] {{
  background: transparent !important;
  border: 1px solid var(--cv-border) !important;
  color: var(--cv-subtext) !important;
  font-weight: 650 !important;
  box-shadow: none !important;
  transform: none !important;
  filter: none !important;
}}
.stButton > button[kind="secondary"]:hover,
.stButton > button[kind="secondaryFormSubmit"]:hover {{
  background: rgba(36,59,107,0.05) !important;
  border-color: rgba(36,59,107,0.22) !important;
  color: var(--cv-text) !important;
}}

.stButton > button:hover {{
  transform: translateY(-1px) !important;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12) !important;
  filter: brightness(1.02) !important;
}}
.stButton > button:active {{ transform: translateY(0) !important; }}

/* Example buttons */
.ex-btn > .stButton > button {{
  background: var(--cv-panel) !important;
  border: 1px solid var(--cv-border) !important;
  color: var(--cv-subtext) !important;
  font-size: 12.5px !important;
  font-weight: 600 !important;
  text-align: left !important;
  padding: 0.5rem 0.75rem !important;
  border-radius: 12px !important;
}}
.ex-btn > .stButton > button:hover {{
  border-color: rgba(36,59,107,0.22) !important;
  background: rgba(36,59,107,0.05) !important;
  color: var(--cv-text) !important;
  transform: translateX(2px) !important;
  box-shadow: none !important;
}}

/* Examples panel cohesion */
.cv-examples-card {{ padding: 16px !important; }}
.cv-examples-head {{
  font-family: {TOK['mono']} !important;
  font-size: 10.5px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  color: var(--cv-muted) !important;
  margin-bottom: 12px !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
}}
.cv-examples-card .stButton {{ margin: 0 0 10px 0 !important; }}
.cv-examples-card .stButton:last-of-type {{ margin-bottom: 0 !important; }}

/* Metrics */
[data-testid="stMetric"] {{
  background: var(--cv-card) !important;
  border: 1px solid var(--cv-border) !important;
  border-radius: 14px !important;
  padding: 16px !important;
  margin-bottom: 16px !important;
}}
[data-testid="stMetricValue"] {{
  font-family: {TOK['mono']} !important;
  font-weight: 800 !important;
}}
[data-testid="stMetricLabel"] {{
  font-size: 12px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.6px !important;
}}

/* Expanders */
[data-testid="stExpander"] {{
  background: var(--cv-card) !important;
  border: 1px solid var(--cv-border) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
}}
[data-testid="stExpander"] > div > div {{ padding: 16px !important; }}

/* Tabs */
.stTabs [data-baseweb="tab"] {{
  font-family: {TOK['sans']} !important;
  font-weight: 600 !important;
  color: var(--cv-muted) !important;
}}
.stTabs [aria-selected="true"] {{ color: var(--cv-accent) !important; }}

/* Dataframes */
[data-testid="stDataFrame"] {{
  border-radius: 12px !important;
  overflow: hidden !important;
  border: 1px solid var(--cv-border) !important;
}}

/* Divider */
hr {{
  border: none !important;
  border-top: 1px solid var(--cv-border-soft) !important;
  margin: 20px 0 !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: rgba(15,23,42,0.05); }}
::-webkit-scrollbar-thumb {{ background: rgba(15,23,42,0.18); border-radius: 6px; }}

/* Prevent charts from being clipped */
.cv-paper,
.cv-verdict-card,
.cv-examples-card {{ overflow: visible !important; }}

/* Badges */
.cv-badge {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--cv-border);
  background: rgba(36,59,107,0.06);
  font-family: {TOK['mono']};
  font-size: 11.5px;
  color: var(--cv-subtext);
  white-space: nowrap;
}}

/* Paper */
.cv-paper {{
  background: var(--cv-card);
  border: 1px solid var(--cv-border);
  border-radius: 16px;
  padding: 20px;
}}

/* Soft note */
.cv-softnote {{
  background: rgba(15,23,42,0.03);
  border: 1px dashed rgba(15,23,42,0.22);
  border-radius: 10px;
  padding: 12px 14px;
  color: var(--cv-subtext);
  font-family: {TOK['mono']};
  font-size: 12px;
  line-height: 1.6;
}}

/* Lucide SVGs */
.cv-ico svg {{
  width: 18px;
  height: 18px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}}

/* Pipeline stepper */
.cv-pipeline {{
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding: 4px 0;
}}
.cv-step {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  font-family: {TOK['mono']};
  font-size: 12px;
  white-space: nowrap;
  transition: all 0.18s ease;
}}
.cv-step.active {{
  background: rgba(36,59,107,0.07);
  border-color: rgba(36,59,107,0.25);
  color: var(--cv-text);
}}
.cv-step.done {{
  background: rgba(15,122,74,0.06);
  border-color: rgba(15,122,74,0.24);
  color: var(--cv-good);
}}
.cv-step.idle {{
  background: rgba(15,23,42,0.02);
  border-color: var(--cv-border);
  color: var(--cv-muted);
}}
.cv-step-connector {{
  width: 24px;
  height: 2px;
  background: var(--cv-border);
  flex-shrink: 0;
}}
.cv-step-connector.done {{ background: rgba(15,122,74,0.35); }}

/* Verdict card */
.cv-verdict-card {{
  border-radius: 18px;
  border: 1px solid;
  padding: 24px;
  position: relative;
  background: var(--cv-card);
  margin-bottom: 20px;
}}

/* Keyboard shortcut hint */
.cv-kbd {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 2px 6px;
  background: rgba(15,23,42,0.04);
  border: 1px solid var(--cv-border);
  border-radius: 6px;
  font-family: {TOK['mono']};
  font-size: 10px;
  color: var(--cv-subtext);
  margin: 0 2px;
}}

 /* ─────────────────────────────────────────────────────────────
    CITATION HEAT HIGHLIGHTING (forensic, non-flashy)
    IMPORTANT: braces are doubled
    ───────────────────────────────────────────────────────────── */
.cv-heat-wrapper {{
  font-family: {TOK['mono']} !important;
  font-size: 13.5px;
  line-height: 1.7;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--cv-border);
  background: var(--cv-card);
}}

.cv-heat-high {{
  background: rgba(180,35,24,0.12);
  border-bottom: 2px solid var(--cv-bad);
  padding: 1px 2px;
  border-radius: 3px;
}}

.cv-heat-med {{
  background: rgba(180,83,9,0.12);
  border-bottom: 2px solid var(--cv-warn);
  padding: 1px 2px;
  border-radius: 3px;
}}

.cv-heat-low {{
  background: rgba(15,122,74,0.08);
  border-bottom: 2px solid var(--cv-good);
  padding: 1px 2px;
  border-radius: 3px;
}}

</style>
"""