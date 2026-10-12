"""Presentation helpers that can run without a Streamlit server."""
from citeverify import AuditResult, ParsedCitation, Signal
from citeverify.parsing import parse_citation
from utils.heatmap import highlight_citation
from utils.pdf_generator import generate_pdf_report

TEXT = "He, K. (2019). Deep residual <b>learning</b> for image recognition. CVPR."


def result(**kw):
    base = dict(verdict="Likely hallucinated", sub="DOI exists but details do not match", tier="DOI registry",
                explanation="Cited 2019; registry lists 2016.", action="Remove <it>.", score=0.05,
                parsed=parse_citation(TEXT),
                signals=[Signal("Year", "fail", "Cited 2019; registry lists 2016."),
                         Signal("First author", "pass", "He is the first author.")])
    base.update(kw)
    return AuditResult(**base)


def test_highlight_escapes_input_and_marks_checked_fields():
    out = highlight_citation(TEXT, result())
    assert "<b>" not in out and "&lt;b&gt;" in out
    assert '<span class="cv-heat-high" title="Cited 2019; registry lists 2016.">2019</span>' in out
    assert '<span class="cv-heat-low"' in out and ">He</span>" in out


def test_highlight_without_parsed_fields():
    r = result(parsed=ParsedCitation(raw="x", cleaned="x"), signals=[])
    assert highlight_citation("a < b", r) == '<div class="cv-heat-wrapper">a &lt; b</div>'


def test_pdf_report_renders_untrusted_text():
    pdf = generate_pdf_report(result(error="timeout <x>"), TEXT, "10.1109/CVPR.2016.90").getvalue()
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000
