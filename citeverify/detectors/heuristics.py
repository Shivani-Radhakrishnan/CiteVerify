"""Tier (fallback): surface-pattern plausibility score from the first version of CiteVerify.

Used only when the citation cannot be looked up (no usable title, registry search
disabled, or the registries are unreachable). The features describe *format* (inline
mention vs. reference-list entry), not whether the cited work exists, so this tier is a
weak, last-resort signal and never returns VERIFIED.
"""
from __future__ import annotations

import re
from typing import Any

from citeverify.detectors import (
    ACTION_REMOVE, ACTION_REVIEW, HALLUCINATED, LIKELY_REAL, NEEDS_REVIEW, Decision,
)
from citeverify.models import Signal

# (feature, direction, weight, description). direction +1 raises the score.
FEATURES: list[tuple[str, int, float, str]] = [
    ("ends_connective", +1, 0.20, "Ends mid-sentence (inline fragment)"),
    ("starts_context", +1, 0.10, "Starts with a context word (inline mention)"),
    ("multi_inline", +1, 0.15, "Several author-year pairs (inline style)"),
    ("year_suffix", +1, 0.15, "Year suffix such as 2023a"),
    ("short_fragment", +1, 0.05, "Short author-year fragment"),
    ("initial_author", -1, 0.15, "Surname + initial (reference-list format)"),
    ("title_phrase", -1, 0.15, "Long title phrase after the year"),
    ("ends_venue", -1, 0.15, "Ends with a venue name"),
    ("many_initials", -1, 0.10, "Many initial-style author names"),
    ("long_entry", -1, 0.05, "Long entry (10+ words)"),
    ("year_first", -1, 0.30, "Starts with a year and no author"),
]
FEATURE_INFO = {name: (direction, desc) for name, direction, _, desc in FEATURES}


def extract_features(text: str) -> dict[str, Any]:
    """Boolean surface features (plus ``word_count``) of a citation string."""
    t = str(text or "").lower().strip()
    if not t:
        return {}
    words = t.split()
    wc = len(words)
    has_ay = bool(re.search(r'[a-z]{3,}\s+(?:et al\.?\s+)?\d{4}', t))
    return {
        'ends_connective': bool(re.search(r'\b(and|or|in|the|that|of|to|for|a|an|with|we|our|this|null|following|based|using|see|cf)\s*$', t)),
        'starts_context': bool(re.search(r'^(the|a|an|in|of|and|or|as|based|following|approach|method|model|work|trained|mirrors|superior|challenging)\b', t)),
        'multi_inline': len(re.findall(r'[a-z]{3,}\s+(?:et al\.?\s+)?\d{4}[a-b]?', t)) >= 2,
        'year_suffix': bool(re.search(r'\d{4}[ab]\b', t)),
        'short_fragment': has_ay and wc <= 12,
        'initial_author': bool(re.findall(r'\b[a-z]{2,}\s+[a-z]{1,2}\s+(?:[a-z]{2,}\s+[a-z]{1,2}\s+)*(19[5-9]\d|20[0-2]\d)\b', t)),
        'title_phrase': bool(re.search(r'(19[5-9]\d|20[0-2]\d)\s+[a-z]{4,}(?:\s+[a-z]{3,}){3,}', t)),
        'ends_venue': bool(re.search(r'(journal|review|conference|proceedings|acl|neurips|icml|iclr|acm|ieee|science|systems|arxiv|nature)\s*$', t)),
        'many_initials': len(re.findall(r'[a-z]{3,}\s+[a-z]{1,3}\b', t)) >= 3,
        'long_entry': wc >= 10,
        'year_first': bool(re.match(r'^\s*(19[5-9]\d|20[0-2]\d)\s+\w+', t)) and not has_ay,
        'word_count': wc,
    }


def plausibility_score(features: dict[str, Any]) -> float:
    """Weighted sum of the features around a 0.5 prior, clipped to [0.02, 0.98]."""
    if not features:
        return 0.3
    s = 0.5
    for name, direction, weight, _ in FEATURES:
        if features.get(name):
            s += direction * weight
    return round(min(max(s, 0.02), 0.98), 4)


#: Heuristics never verify anything, so their score is capped below the VERIFIED band.
MAX_HEURISTIC_SCORE = 0.69


def check(text: str) -> Decision:
    feats = extract_features(text)
    score = min(plausibility_score(feats), MAX_HEURISTIC_SCORE)
    signals = [
        Signal(desc, "pass" if direction > 0 else "warn", "Inline-style signal" if direction > 0 else "Reference-entry signal")
        for name, direction, _, desc in FEATURES if feats.get(name)
    ] or [Signal("Surface patterns", "info", "No strong structural signals.")]
    if score >= 0.50:
        verdict, sub, action = LIKELY_REAL, "Moderate heuristic plausibility", ACTION_REVIEW
    elif score >= 0.20:
        verdict, sub, action = NEEDS_REVIEW, "Low heuristic plausibility", ACTION_REVIEW
    else:
        verdict, sub, action = HALLUCINATED, "Very low heuristic plausibility", ACTION_REMOVE
    return Decision(
        score=score, verdict=verdict, sub=sub,
        explanation="Not verified against a registry; scored from surface patterns only. "
                    + "; ".join(s.name for s in signals) + ".",
        action=action, signals=signals, features=feats,
    )
