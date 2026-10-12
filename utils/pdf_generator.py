"""
PDF report for a single audit result.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from citeverify import AuditResult, __version__
from config import TOK

_LABEL_COLOR = {"VERIFIED": TOK["good"], "UNCERTAIN": TOK["warn"], "HALLUCINATED": TOK["bad"]}
_STATUS_TEXT = {"pass": "OK", "fail": "Conflict", "warn": "Check", "info": "Info", "skip": "Not checked"}


def _p(text: object, style) -> Paragraph:
    """Paragraph with reportlab markup characters escaped."""
    return Paragraph(escape("" if text is None else str(text)), style)


def generate_pdf_report(result: AuditResult, citation_text: str, doi_input: str = "") -> BytesIO:
    """Render ``result`` as a one-page PDF and return it as an in-memory buffer."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    body = styles["Normal"]
    title = ParagraphStyle("cvTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=14,
                           textColor=colors.HexColor(TOK["accent"]))
    heading = ParagraphStyle("cvHeading", parent=styles["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=6,
                             textColor=colors.HexColor(TOK["text"]))
    label = ParagraphStyle("cvLabel", parent=body, fontSize=14, leading=18,
                           textColor=colors.HexColor(_LABEL_COLOR.get(result.label, TOK["text"])))
    grid = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(TOK["text"])),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(TOK["bg"])),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(TOK["border"])),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])

    story = [
        _p("CiteVerify citation audit", title),
        _p(f"Generated {datetime.now():%Y-%m-%d %H:%M} · CiteVerify {__version__} · "
           f"threshold {result.threshold:.2f}", body),
        Spacer(1, 10),
        _p("Input", heading), _p(citation_text, body),
    ]
    if doi_input:
        story.append(_p(f"DOI: {doi_input}", body))
    story += [
        _p("Verdict", heading),
        _p(f"{result.label} — {result.verdict}: {result.sub}", label),
        _p(f"Score {result.score:.2f} · decided by {result.tier}", body),
        _p(result.explanation, body),
        _p(f"Recommended action: {result.action}", body),
    ]
    if result.error:
        story.append(_p(f"Registry error: {result.error}", body))
    if result.signals:
        rows = [["Check", "Result", "Detail"]] + [
            [_p(s.name, body), _STATUS_TEXT.get(s.status, s.status), _p(s.detail, body)] for s in result.signals
        ]
        t = Table(rows, colWidths=[110, 70, 300])
        t.setStyle(grid)
        story += [_p("Evidence", heading), t]
    if result.record:
        r = result.record
        story += [_p("Matched record", heading),
                  _p(f"{r.title} — {', '.join(r.authors[:5])} ({r.year or 'n.d.'}). {r.source}. {r.url}", body)]
    story += [
        _p("Limitations", heading),
        _p("Verdicts depend on Crossref, DataCite and arXiv coverage. Works those registries do not index "
           "(many books, theses and reports) cannot be confirmed. Verify important references by hand.", body),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer
