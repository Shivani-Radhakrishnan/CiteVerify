"""Tier (legacy, off by default): the hard-coded "known papers" lookup table.

This table shipped with the first version of CiteVerify. Its entries are keyed by the
first author's surname plus a year and a title keyword. A fixed list cannot generalise
to papers it doesn't contain, and it cannot tell a correct citation of a listed paper
from a fabricated one, so registry checks replaced it. See ``evaluation/README.md`` for
the ablation.

It is kept only so the ablation can be reproduced: ``AuditConfig(use_known_papers=True)``.
"""
from __future__ import annotations

import re
from typing import Optional

from citeverify.detectors import ACTION_NONE, ACTION_REMOVE, HALLUCINATED, VERIFIED, Decision
from citeverify.models import Signal

KNOWN_REAL: dict[str, tuple[int, Optional[str]]] = {
    'vaswani': (2017, 'attention is all you need'), 'sulem': (2021, 'bleurt'),
    'harwood': (2023, 'bibliographic'), 'bharadwaj': (2022, 'referential integrity'),
    'okafor': (2023, 'bibliometric'), 'rao': (2024, 'graphbased'), 'larsen': (2023, 'synthetic doi'),
    'owens': (2022, 'venue scoring'), 'morgan': (2023, 'interdisciplinary citation'),
    'delgado': (2024, 'contextaware'), 'feldman': (2020, None), 'geiping': (2025, None),
    'mcleish': (2025, None), 'pham': (2025, None), 'baldock': (2021, None), 'yang': (2023, None),
    'fan': (2024, None), 'silver': (2017, 'mastering'), 'hinton': (2006, None), 'lecun': (1998, None),
    'hochreiter': (1997, None), 'goodfellow': (2014, None), 'brown': (2020, 'language models are few'),
    'pennington': (2014, 'glove'),
}

KNOWN_FAKE: dict[str, tuple[int, Optional[str]]] = {
    'lewis': (2020, 'retrievalaugmented'), 'pedregosa': (2011, 'scikitlearn'),
    'maynez': (2020, 'faithfulness and factuality'), 'bender': (2021, 'dangers'),
    'dziri': (2022, 'faithfulness in opendomain'), 'ji': (2023, 'survey of hallucination'),
    'devlin': (2019, 'bert pretraining'), 'amershi': (2014, 'power to the people'),
    'ouyang': (2022, 'training language models to follow'), 'zellers': (2019, 'defending'),
    'thorne': (2018, 'fever'), 'karpukhin': (2020, 'dense passage'),
    'newman': (2003, 'structure and function of complex networks'),
    'radford': (2019, 'language models are unsupervised'), 'reimers': (2019, 'sentencebert'),
    'lin': (2004, 'rouge'), 'kleinberg': (1999, 'authoritative sources'), 'peng': (2023, 'check your facts'),
}


def lookup(text: str) -> Optional[float]:
    """Original matching rule: 0.85 for a known-real hit, 0.05 for a known-fake hit."""
    t = str(text or "").lower().strip()
    first = next((w for w in t.split() if len(w) >= 3 and w.isalpha()), None)
    if not first:
        return None
    yrs = re.findall(r'\b(19[5-9]\d|20[0-2]\d)\b', t)
    yr = int(yrs[0]) if yrs else None
    for table, value in ((KNOWN_REAL, 0.85), (KNOWN_FAKE, 0.05)):
        if first in table:
            year, keyword = table[first]
            if (year is None or yr == year) and (keyword is None or keyword in t):
                return value
    return None


def check(cleaned_text: str) -> Optional[Decision]:
    value = lookup(cleaned_text)
    if value is None:
        return None
    if value >= 0.70:
        return Decision(
            score=value, verdict=VERIFIED, sub="Known-paper table match",
            explanation="Matches an entry in the legacy known-real table.", action=ACTION_NONE,
            signals=[Signal("Known-papers table", "pass", "Listed as known real.")],
        )
    return Decision(
        score=value, verdict=HALLUCINATED, sub="Known-fake table match",
        explanation="Matches an entry in the legacy known-fake table.", action=ACTION_REMOVE,
        signals=[Signal("Known-papers table", "fail", "Listed as known fake.")],
    )
