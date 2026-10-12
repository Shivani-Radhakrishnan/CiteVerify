"""Binary classification metrics (positive class = hallucinated), without scikit-learn."""
from __future__ import annotations

from typing import Sequence


def binary_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict:
    """Accuracy, precision, recall, F1, false-positive rate and the confusion counts.

    ``1`` means hallucinated/fabricated. Undefined ratios (no positives predicted, etc.)
    are reported as 0.0.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred differ in length")
    pairs = list(zip((int(t) for t in y_true), (int(p) for p in y_pred)))
    tp = sum(t == 1 and p == 1 for t, p in pairs)
    fp = sum(t == 0 and p == 1 for t, p in pairs)
    fn = sum(t == 1 and p == 0 for t, p in pairs)
    tn = sum(t == 0 and p == 0 for t, p in pairs)
    n = len(pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": n,
        "accuracy": (tp + tn) / n if n else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
    }
