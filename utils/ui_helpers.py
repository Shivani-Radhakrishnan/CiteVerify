"""
UI helper functions for CiteVerify (presentation only).

Everything rendered with ``unsafe_allow_html`` goes through :func:`esc`, because
citation text, registry titles and error messages are untrusted input.
"""
from __future__ import annotations

import html
from typing import Iterable, Optional

import pandas as pd
import streamlit as st

from citeverify import AuditConfig, Auditor, AuditResult, Tier
from citeverify.clients.http import HttpClient
from config import NAV_ITEMS, TOK


def esc(value: object) -> str:
    """HTML-escape any value for safe interpolation into markup."""
    return html.escape("" if value is None else str(value), quote=True)


# ─────────────────────────────────────────────────────────────────────────────
# Lucide-style inline SVGs
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
    "search": '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
    "sigma": '<svg viewBox="0 0 24 24"><path d="M19 5H7l6 7-6 7h12"/></svg>',
    # Verdict
    "check-circle": '<svg viewBox="0 0 24 24"><path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="M22 4 12 14l-3-3"/></svg>',
    "alert-triangle": '<svg viewBox="0 0 24 24"><path d="m10.3 4.3-8.6 15A2 2 0 0 0 3.4 22h17.2a2 2 0 0 0 1.7-3l-8.6-15a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
    "x-circle": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6"/><path d="M9 9l6 6"/></svg>',
    "wifi-off": '<svg viewBox="0 0 24 24"><path d="M2 2l20 20"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M5 12.9a10 10 0 0 1 5.2-2.8"/><path d="M19 12.9a10 10 0 0 0-2.4-1.7"/><path d="M12 20h.01"/></svg>',
    # Actions
    "file-text": '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/></svg>',
    "sliders": '<svg viewBox="0 0 24 24"><path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M2 14h4"/><path d="M10 12h4"/><path d="M18 16h4"/></svg>',
    "history": '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 3v6h6"/><path d="M12 7v5l4 2"/></svg>',
}


def lucide(name: str) -> str:
    """Return an inline SVG (Lucide-style) for presentation."""
    return _LUCIDE.get(name, '<svg viewBox="0 0 24 24"><path d="M4 12h16"/></svg>')


def strip_ui_emoji(text: str) -> str:
    """Remove emoji prefixes used by older UI labels."""
    if not text:
        return text
    for p in ("🔬 ", "🧪 ", "📦 ", "⚖️ ", "📊 ", "📘 ", "✅ ", "⚠️ ", "🚨 ", "🔗 ", "📅 ", "📚 ", "🧮 ", "🟢 ", "🔴 "):
        text = text.replace(p, "")
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Auditor (shared HTTP cache across reruns and sessions)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _http_client() -> HttpClient:
    return HttpClient(timeout=8.0, retries=2)


def get_auditor() -> Auditor:
    """Auditor configured from the sidebar settings."""
    cfg = AuditConfig(
        threshold=float(st.session_state.get("threshold", 0.20)),
        use_search=bool(st.session_state.get("use_search", True)),
        use_known_papers=bool(st.session_state.get("use_known_papers", False)),
    )
    return Auditor(cfg, _http_client())


# ─────────────────────────────────────────────────────────────────────────────
# Layout primitives
# ─────────────────────────────────────────────────────────────────────────────

def hero(title: str, subtitle: str, badges: Optional[Iterable[str]] = None) -> None:
    """Page header with title, subtitle and badges."""
    badge_html = "".join(f'<span class="cv-badge">{esc(b)}</span>' for b in (badges or []))
    st.markdown(
        f'<div class="cv-hero">'
        f'<div class="cv-hero-title">{esc(strip_ui_emoji(title))}</div>'
        f'<div class="cv-hero-sub">{esc(strip_ui_emoji(subtitle))}</div>'
        f'<div class="cv-hero-badges">{badge_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def section_label(icon: str, text: str) -> None:
    st.markdown(
        f'<div class="cv-section-label"><span class="cv-ico">{lucide(icon)}</span>'
        f"<span>{esc(text)}</span></div>",
        unsafe_allow_html=True,
    )


def label_palette(label: str) -> tuple[str, str, str]:
    """(text colour, background, border) for a VERIFIED/UNCERTAIN/HALLUCINATED label."""
    if label == "VERIFIED":
        return TOK["good"], "rgba(15,122,74,0.08)", "rgba(15,122,74,0.30)"
    if label == "UNCERTAIN":
        return TOK["warn"], "rgba(180,83,9,0.08)", "rgba(180,83,9,0.30)"
    return TOK["bad"], "rgba(180,35,24,0.08)", "rgba(180,35,24,0.30)"


_LABEL_ICON = {"VERIFIED": "check-circle", "UNCERTAIN": "alert-triangle", "HALLUCINATED": "x-circle"}

# Pipeline stages shown in the stepper, in order.
_STAGES = [
    (Tier.TEMPORAL, "calendar", "Temporal"),
    (Tier.DOI, "link", "DOI registry"),
    (Tier.KNOWN, "database", "Known table"),
    (Tier.SEARCH, "search", "Title search"),
    (Tier.HEURISTIC, "sigma", "Heuristics"),
]


def tier_stepper(result: AuditResult) -> None:
    """Show which stages ran, which were skipped, and which one decided."""
    status = {s.tier: (s.status, s.note) for s in result.trace}
    parts = []
    for i, (tier, icon, name) in enumerate(_STAGES):
        if tier == Tier.KNOWN and tier not in status:
            continue  # only shown when the legacy table is switched on
        st_, note = status.get(tier, ("idle", ""))
        cls, dot = {"decided": ("active", "●"), "passed": ("done", "✓"), "skipped": ("idle", "–")}.get(st_, ("idle", "·"))
        tip = f"{name}: {st_}" + (f" ({note})" if note else "")
        parts.append(
            f'<div class="cv-step {cls}" title="{esc(tip)}"><span class="cv-step-dot">{dot}</span>'
            f'<span class="cv-ico">{lucide(icon)}</span><span>{esc(name)}</span></div>'
        )
        parts.append('<div class="cv-step-connector"></div>')
    st.markdown(f'<div class="cv-pipeline">{"".join(parts[:-1])}</div>', unsafe_allow_html=True)


def _risk_line(result: AuditResult) -> str:
    """One line with the learned model's calibrated risk, when it is available."""
    if result.risk is None:
        return ""
    pct = result.risk * 100
    shown = "<1%" if pct < 1 else (">99%" if pct > 99 else f"{pct:.0f}%")
    return (f'<div class="cv-verdict-meta" style="margin-top:10px;">Learned risk of fabrication: '
            f"<b>{shown}</b> (calibrated model over this evidence)</div>")


def verdict_card(result: AuditResult) -> None:
    """Headline verdict: label, reason, score, explanation and recommended action."""
    color, bg, border = label_palette(result.label)
    pct = int(round(result.score * 100))
    error = ""
    if result.error:
        error = (
            f'<div class="cv-error"><span class="cv-ico">{lucide("wifi-off")}</span>'
            f"<span>A registry could not be reached, so this verdict is provisional: {esc(result.error)}</span></div>"
        )
    st.markdown(
        f'<div class="cv-verdict-card" style="border-color:{border};">'
        f'<div class="cv-verdict-top">'
        f'<div style="min-width:0;flex:1;">'
        f'<div class="cv-pill" style="color:{color};background:{bg};border-color:{border};">'
        f'<span class="cv-ico">{lucide(_LABEL_ICON.get(result.label, "alert-triangle"))}</span>{esc(result.label)}</div>'
        f'<div class="cv-verdict-title">{esc(result.verdict)} · {esc(result.sub)}</div>'
        f'<div class="cv-verdict-meta">Decided by: {esc(result.tier)}</div>'
        f"</div>"
        f'<div class="cv-score"><div class="cv-score-label">Score</div>'
        f'<div class="cv-score-value" style="color:{color};">{result.score:.2f}</div>'
        f'<div class="cv-score-label">threshold {result.threshold:.2f}</div></div>'
        f"</div>"
        f'<div class="cv-progress-bar"><div style="width:{pct}%;background:{color};"></div></div>'
        f'<div class="cv-verdict-grid">'
        f'<div class="cv-panel"><div class="cv-panel-label">Why</div><div>{esc(result.explanation)}</div></div>'
        f'<div class="cv-panel" style="background:{bg};border-color:{border};">'
        f'<div class="cv-panel-label">Recommended action</div><div style="font-weight:700;">{esc(result.action)}</div></div>'
        f"</div>{_risk_line(result)}{error}</div>",
        unsafe_allow_html=True,
    )


_SIGNAL_STYLE = {
    "pass": ("✓", TOK["good"]),
    "fail": ("✕", TOK["bad"]),
    "warn": ("!", TOK["warn"]),
    "info": ("i", TOK["muted"]),
    "skip": ("–", TOK["muted"]),
}


def evidence_panel(result: AuditResult) -> None:
    """Every check that ran, with its outcome."""
    if not result.signals:
        st.info("No evidence recorded for this result.")
        return
    rows = []
    for s in result.signals:
        mark, color = _SIGNAL_STYLE.get(s.status, ("·", TOK["muted"]))
        rows.append(
            f'<div class="cv-signal"><span class="cv-signal-mark" style="color:{color};border-color:{color};">{mark}</span>'
            f'<div><div class="cv-signal-name">{esc(s.name)}</div>'
            f'<div class="cv-signal-detail">{esc(s.detail)}</div></div></div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def comparison_table(result: AuditResult) -> pd.DataFrame:
    """Parsed citation fields side by side with the matched registry record."""
    p, r = result.parsed, result.record
    fields = {
        "First author": (p.first_author if p else None, r.authors[0] if r and r.authors else None),
        "Year": (p.year if p else None, "/".join(map(str, sorted(r.years))) if r and r.years else None),
        "Title": (p.title if p else None, r.title if r else None),
        "Venue": (p.venue if p else None, r.venue if r else None),
        "DOI": (p.doi if p else None, r.doi if r else None),
    }
    return pd.DataFrame(
        [{"Field": k, "Citation says": str(v[0]) if v[0] else "—", "Registry says": str(v[1]) if v[1] else "—"}
         for k, v in fields.items()]
    )


def record_link(result: AuditResult) -> None:
    r = result.record
    if r and r.url:
        st.markdown(f"Matched record: [{r.title[:90]}]({r.url}) ({r.source})")


def feature_badges(features: dict) -> None:
    """Two-column grid of the heuristic surface features (fallback tier only)."""
    from citeverify.detectors.heuristics import FEATURES

    def chip(name: str, desc: str, positive: bool) -> str:
        active = bool(features.get(name))
        color = TOK["good"] if positive else TOK["bad"]
        cls = "cv-feat-chip active" if active else "cv-feat-chip"
        return (f'<div class="{cls}"><span style="color:{color};font-weight:900;">{"✓" if active else "—"}</span>'
                f"<span>{esc(desc)}</span></div>")

    inline = "".join(chip(n, d, True) for n, sign, _, d in FEATURES if sign > 0)
    entry = "".join(chip(n, d, False) for n, sign, _, d in FEATURES if sign < 0)
    st.markdown(
        f'<div class="cv-feat-grid"><div class="cv-feat-col"><div class="cv-feat-head" style="color:{TOK["good"]};">'
        f'Raises score</div>{inline}</div><div class="cv-feat-col"><div class="cv-feat-head" style="color:{TOK["bad"]};">'
        f"Lowers score</div>{entry}</div></div>",
        unsafe_allow_html=True,
    )


def idle_state(title: str, body: str, icon: str = "flask-conical") -> None:
    st.markdown(
        f'<div class="cv-idle-state"><div class="cv-ico cv-idle-icon">{lucide(icon)}</div>'
        f'<div class="cv-idle-title">{esc(title)}</div><div class="cv-idle-body">{esc(body)}</div></div>',
        unsafe_allow_html=True,
    )


def footer(text: str) -> None:
    st.markdown(f'<div class="cv-footer">{esc(text)}</div>', unsafe_allow_html=True)


def style_label_bg(v: str) -> str:
    """Dataframe cell style for a label column."""
    color, bg, _ = label_palette(v)
    return f"background-color:{bg}; color:{color}; font-weight:700"


def style_score(v) -> str:
    """Dataframe cell style for a score column."""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return ""
    color = TOK["good"] if x >= 0.7 else TOK["warn"] if x >= 0.2 else TOK["bad"]
    return f"color:{color}; font-weight:700"


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Brand, navigation and audit settings (stored in ``st.session_state``)."""
    st.markdown(
        f'<div class="cv-brand"><div class="cv-brand-mark">CV</div><div>'
        f'<div class="cv-brand-name">CiteVerify</div>'
        f'<div class="cv-brand-sub">Citation hallucination detection</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cv-side-label">Navigation</div>', unsafe_allow_html=True)
    for icon_name, label, key in NAV_ITEMS:
        active = st.session_state.get("page") == key
        ico_col, btn_col = st.columns([0.16, 0.84], gap="small")
        with ico_col:
            st.markdown(
                f'<div class="cv-nav-ico" style="opacity:{1.0 if active else 0.7};">'
                f'<span class="cv-ico">{lucide(icon_name)}</span></div>',
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button(label, key=f"navbtn_{key}", use_container_width=True,
                         type="primary" if active else "secondary"):
                st.session_state["page"] = key
                st.rerun()

    st.markdown('<div class="cv-side-label" style="margin-top:14px;">Audit settings</div>', unsafe_allow_html=True)
    st.slider("Hallucination threshold", 0.05, 0.60, 0.20, 0.05, key="threshold",
              help="Scores below this are labelled HALLUCINATED. The benchmark results use 0.20.")
    st.toggle("Title search when there is no DOI", value=True, key="use_search",
              help="Look the citation up in Crossref and arXiv by title. Off: fall back to surface heuristics.")
    st.toggle("Legacy known-papers table", value=False, key="use_known_papers",
              help="The v1 lookup table. Not recommended: it flags several real, famous papers as fake. "
                   "See evaluation/README.md.")
    st.checkbox("Show heuristic features", value=True, key="show_features")
    st.checkbox("Show cleaned input", value=True, key="show_compare")

    stages = "".join(
        f'<div class="cv-side-stage"><span class="cv-side-num">{i:02d}</span>{esc(name)}</div>'
        for i, name in enumerate(["Temporal check", "DOI registry", "Title search", "Heuristic fallback"], 1)
    )
    st.markdown(f'<div class="cv-side-label" style="margin-top:14px;">Detection pipeline</div>{stages}',
                unsafe_allow_html=True)
