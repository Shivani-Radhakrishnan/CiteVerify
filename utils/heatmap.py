import re
from config import TOK

def highlight_citation(text: str, audit_result) -> str:
    """
    Returns HTML with suspicious segments highlighted.
    Does NOT modify detection logic.
    """

    highlighted = text

    # 1️⃣ Future year (high severity)
    years = re.findall(r"\b(20\d{2}|19\d{2})\b", text)
    for y in years:
        try:
            year = int(y)
            if year > 2025:
                highlighted = highlighted.replace(
                    y,
                    f'<span class="cv-heat-high" title="Future year detected">{y}</span>'
                )
        except:
            pass

    # 2️⃣ Suspicious many-initial author pattern (medium severity)
    if re.search(r"\b[A-Z]\.\s?[A-Z]\.", text):
        highlighted = re.sub(
            r"\b[A-Z]\.\s?[A-Z]\.",
            lambda m: f'<span class="cv-heat-med" title="Initial-heavy author pattern">{m.group(0)}</span>',
            highlighted
        )

    # 3️⃣ Suspicious venue words
    suspicious_venues = [
        "International Review",
        "Global Neural Symposium",
        "Journal of Future AI",
        "Universal Scaling Theorem"
    ]

    for venue in suspicious_venues:
        if venue in highlighted:
            highlighted = highlighted.replace(
                venue,
                f'<span class="cv-heat-high" title="Unverified or suspicious venue">{venue}</span>'
            )

    return f'<div class="cv-heat-wrapper">{highlighted}</div>'