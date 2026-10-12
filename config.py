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

/* ─────────────────────────────────────────────────────────────
   COMPONENTS (hero, verdict card, evidence, sidebar, states)
   ───────────────────────────────────────────────────────────── */
.cv-hero {{ margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid var(--cv-border-soft); }}
.cv-hero-title {{ font-size:1.75rem; font-weight:800; letter-spacing:-0.6px; line-height:1.15; color:var(--cv-text); }}
.cv-hero-sub {{ margin-top:8px; color:var(--cv-muted); font-size:13.5px; max-width:80ch; line-height:1.65; }}
.cv-hero-badges {{ margin-top:14px; display:flex; flex-wrap:wrap; gap:8px; }}

.cv-section-label {{
  font-family:{TOK['mono']}; font-size:10.5px; text-transform:uppercase; letter-spacing:1.2px;
  color:var(--cv-muted); margin-bottom:8px; display:flex; align-items:center; gap:6px;
}}
.cv-section-label .cv-ico {{ color:var(--cv-accent); }}

.cv-step-dot {{ font-weight:800; min-width:10px; text-align:center; }}

.cv-pill {{
  display:inline-flex; align-items:center; gap:8px; border-radius:999px; padding:6px 12px;
  border:1px solid; font-weight:800; font-size:13px; letter-spacing:0.02em; margin-bottom:12px;
}}
.cv-verdict-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }}
.cv-verdict-title {{ font-size:1.05rem; font-weight:750; color:var(--cv-text); margin-bottom:6px; }}
.cv-verdict-meta {{ color:var(--cv-muted); font-family:{TOK['mono']}; font-size:12px; }}
.cv-score {{ text-align:right; min-width:120px; flex-shrink:0; }}
.cv-score-label {{ font-family:{TOK['mono']}; font-size:11px; color:var(--cv-muted); text-transform:uppercase; letter-spacing:1px; }}
.cv-score-value {{ font-family:{TOK['mono']}; font-weight:900; font-size:2.1rem; line-height:1.1; letter-spacing:-0.8px; }}
.cv-progress-bar {{ height:6px; border-radius:999px; background:rgba(15,23,42,0.06); margin-top:16px; overflow:hidden; }}
.cv-progress-bar > div {{ height:100%; border-radius:999px; transition:width 0.45s ease; }}
.cv-verdict-grid {{ display:grid; grid-template-columns:1.25fr 0.95fr; gap:12px; margin-top:16px; }}
@media (max-width: 900px) {{ .cv-verdict-grid {{ grid-template-columns:1fr; }} }}
.cv-panel {{
  background:rgba(15,23,42,0.02); border:1px solid var(--cv-border-soft); border-radius:14px; padding:14px;
  color:var(--cv-subtext); line-height:1.65; font-size:13.5px;
}}
.cv-panel-label {{
  font-size:10px; color:var(--cv-muted); font-family:{TOK['mono']}; text-transform:uppercase;
  letter-spacing:1.2px; margin-bottom:8px;
}}
.cv-error {{
  display:flex; gap:8px; align-items:center; margin-top:12px; padding:10px 12px; border-radius:10px;
  background:rgba(180,83,9,0.07); border:1px solid rgba(180,83,9,0.3); color:var(--cv-warn); font-size:13px;
}}

.cv-signal {{
  display:flex; gap:12px; align-items:flex-start; padding:10px 12px; margin-bottom:8px;
  border:1px solid var(--cv-border-soft); border-radius:12px; background:var(--cv-card);
}}
.cv-signal-mark {{
  width:22px; height:22px; flex-shrink:0; border-radius:50%; border:1.5px solid; display:flex;
  align-items:center; justify-content:center; font-weight:900; font-size:12px; font-family:{TOK['mono']};
}}
.cv-signal-name {{ font-weight:700; color:var(--cv-text); font-size:13px; }}
.cv-signal-detail {{ color:var(--cv-muted); font-size:12.5px; line-height:1.55; margin-top:2px; }}

.cv-feat-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.cv-feat-col {{ display:flex; flex-direction:column; gap:6px; }}
.cv-feat-head {{ font-family:{TOK['mono']}; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:1.2px; }}
.cv-feat-chip {{
  display:flex; gap:10px; align-items:center; padding:7px 10px; border-radius:10px; font-size:12.5px;
  border:1px solid var(--cv-border-soft); color:var(--cv-muted); opacity:0.6;
}}
.cv-feat-chip.active {{ opacity:1; color:var(--cv-text); border-color:var(--cv-border); background:rgba(36,59,107,0.04); }}

.cv-idle-state {{
  display:flex; flex-direction:column; align-items:center; text-align:center; padding:40px 16px;
  border:1px dashed var(--cv-border); border-radius:16px; background:var(--cv-card); margin-top:12px;
}}
.cv-idle-icon {{ color:var(--cv-accent); opacity:0.7; margin-bottom:12px; }}
.cv-idle-title {{ font-weight:700; font-size:15px; color:var(--cv-subtext); margin-bottom:6px; }}
.cv-idle-body {{ font-size:13px; color:var(--cv-muted); max-width:52ch; line-height:1.6; }}

.cv-footer {{
  text-align:center; color:var(--cv-muted); font-family:{TOK['mono']}; font-size:11px;
  border-top:1px solid var(--cv-border-soft); margin-top:28px; padding-top:14px;
}}

.cv-brand {{ display:flex; align-items:center; gap:10px; padding:8px 4px 14px; border-bottom:1px solid var(--cv-border-soft); margin-bottom:12px; }}
.cv-brand-mark {{
  width:34px; height:34px; border-radius:12px; background:var(--cv-accent); color:#fff; font-weight:900;
  display:flex; align-items:center; justify-content:center; letter-spacing:-0.5px;
}}
.cv-brand-name {{ font-size:1.18rem; font-weight:800; letter-spacing:-0.4px; color:var(--cv-text); }}
.cv-brand-sub {{ font-size:11.5px; color:var(--cv-muted); font-family:{TOK['mono']}; }}
.cv-side-label {{
  font-size:10.5px; color:var(--cv-muted); font-family:{TOK['mono']}; text-transform:uppercase;
  letter-spacing:1.2px; padding:0 2px 6px;
}}
.cv-nav-ico {{ margin-top:6px; display:flex; justify-content:center; color:var(--cv-accent); }}
.cv-side-stage {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; font-family:{TOK['mono']}; font-size:11.5px; color:var(--cv-subtext); }}
.cv-side-num {{
  width:22px; height:20px; border-radius:6px; background:rgba(36,59,107,0.08); border:1px solid rgba(36,59,107,0.18);
  display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:800; color:var(--cv-accent);
}}

</style>
"""
