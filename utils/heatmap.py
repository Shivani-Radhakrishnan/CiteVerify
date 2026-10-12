"""
Highlight the parts of a citation that the registry checks confirmed or contradicted.
"""
from __future__ import annotations

import html
import re

from citeverify import AuditResult

# signal status -> CSS class (see config.CSS_STYLES)
_CLASS = {"fail": "cv-heat-high", "warn": "cv-heat-med", "pass": "cv-heat-low"}
_FIELD_SIGNALS = {"Title": "title", "Year": "year", "Publication year": "year", "First author": "first_author"}


def highlight_citation(text: str, result: AuditResult) -> str:
    """Return escaped HTML of ``text`` with the checked fields underlined.

    Red: contradicted by the registry (or impossible). Amber: small discrepancy.
    Green: confirmed. Fields that were not checked are left plain.
    """
    text = text or ""
    parsed = result.parsed
    spans: list[tuple[int, int, str, str]] = []
    if parsed:
        values = {"title": parsed.title, "year": str(parsed.year) if parsed.year else "",
                  "first_author": parsed.first_author or ""}
        status: dict[str, tuple[str, str]] = {}
        for s in result.signals:
            field = _FIELD_SIGNALS.get(s.name)
            if field and s.status in _CLASS:
                # a failing check wins over a passing one for the same field
                if field not in status or s.status == "fail":
                    status[field] = (s.status, s.detail)
        for field, (st, detail) in status.items():
            value = values.get(field)
            if not value:
                continue
            m = re.search(re.escape(value), text, flags=re.IGNORECASE)
            if m:
                spans.append((m.start(), m.end(), _CLASS[st], detail))

    spans.sort()
    out, pos = [], 0
    for start, end, cls, detail in spans:
        if start < pos:
            continue  # overlapping span; keep the first
        out.append(html.escape(text[pos:start]))
        out.append(f'<span class="{cls}" title="{html.escape(detail, quote=True)}">'
                   f"{html.escape(text[start:end])}</span>")
        pos = end
    out.append(html.escape(text[pos:]))
    return f'<div class="cv-heat-wrapper">{"".join(out)}</div>'
