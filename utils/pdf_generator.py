"""
PDF Generation for CiteVerify Reports
"""
from io import BytesIO
from datetime import datetime
from utils.auditor import extract_core_citation

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    import streamlit as st
except ImportError:
    st.warning("Install reportlab for PDF export: pip install reportlab")


def generate_pdf_report(result, citation_text, doi_input, run_id, config_hash):
    """Generate a PDF report for the audit result"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#60a5fa'),
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#e2e8f0'),
    )
    
    # Build story
    story = []
    
    # Title
    story.append(Paragraph("CiteVerify - Citation Audit Report", title_style))
    
    # Metadata
    metadata = [
        ['Run ID:', run_id],
        ['Config Hash:', config_hash],
        ['Timestamp:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['App Version:', 'v1.0'],
        ['Threshold:', f"{st.session_state.get('threshold', 0.20):.2f}"],
    ]
    
    metadata_table = Table(metadata, hAlign='LEFT')
    metadata_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0c1526')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(metadata_table)
    story.append(Spacer(1, 20))
    
    # Input
    story.append(Paragraph("Input", heading_style))
    story.append(Paragraph(f"<b>Original:</b> {citation_text}", styles['Normal']))
    cleaned = extract_core_citation(citation_text)
    story.append(Paragraph(f"<b>Cleaned:</b> {cleaned}", styles['Normal']))
    if doi_input:
        story.append(Paragraph(f"<b>DOI:</b> {doi_input}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Verdict
    story.append(Paragraph("Verdict", heading_style))
    verdict_color = colors.HexColor('#22c55e') if result.label == "VERIFIED" else \
                   colors.HexColor('#f59e0b') if result.label == "UNCERTAIN" else \
                   colors.HexColor('#ef4444')
    
    verdict_text = f"<font color={verdict_color.hexval}><b>{result.label}</b></font> - {result.verdict}"
    story.append(Paragraph(verdict_text, styles['Normal']))
    story.append(Paragraph(f"<b>Score:</b> {result.score:.3f}", styles['Normal']))
    story.append(Paragraph(f"<b>Tier:</b> {result.tier}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Evidence
    story.append(Paragraph("Evidence", heading_style))
    evidence_data = []
    
    # Add evidence based on features
    if hasattr(result, 'features') and result.features:
        for feature, active in result.features.items():
            if active:
                strength = "Strong" if feature in ["doi_valid", "year_valid"] else \
                         "Moderate" if feature in ["title_phrase", "ends_venue"] else "Weak"
                evidence_data.append([feature, strength, "Active"])
    
    evidence_table = Table([["Feature", "Strength", "Status"]] + evidence_data)
    evidence_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0c1526')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2d45')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(evidence_table)
    story.append(Spacer(1, 20))
    
    # Limitations
    story.append(Paragraph("Limitations", heading_style))
    story.append(Paragraph("This audit is based on heuristic analysis and pattern matching. "
                          "For critical applications, verify results through additional means. "
                          "The system may not detect all types of hallucinated citations, "
                          "especially those that closely resemble real citations.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer