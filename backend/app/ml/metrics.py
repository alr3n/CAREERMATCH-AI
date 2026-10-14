"""Ranking and extraction metrics.

Relevance labels are graded integers (0 = not relevant, 1 = partially
relevant, 2 = highly relevant). For binary metrics (precision/recall/MRR) a
label ≥ ``threshold`` counts as relevant.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def precision_at_k(ranked_labels: Sequence[int], k: int, threshold: int = 1) -> float:
    top = list(ranked_labels[:k])
    if k <= 0:
        return 0.0
    return sum(1 for label in top if label >= threshold) / k


def recall_at_k(ranked_labels: Sequence[int], k: int, threshold: int = 1) -> float | None:
    total_relevant = sum(1 for label in ranked_labels if label >= threshold)
    if total_relevant == 0:
        return None  # undefined: no relevant items for this query
    return sum(1 for label in ranked_labels[:k] if label >= threshold) / total_relevant


def dcg_at_k(labels: Sequence[int], k: int) -> float:
    return sum((2**label - 1) / math.log2(i + 2) for i, label in enumerate(labels[:k]))


def ndcg_at_k(ranked_labels: Sequence[int], k: int) -> float | None:
    ideal = dcg_at_k(sorted(ranked_labels, reverse=True), k)
    if ideal == 0:
        return None
    return dcg_at_k(ranked_labels, k) / ideal


def reciprocal_rank(ranked_labels: Sequence[int], threshold: int = 1) -> float:
    for i, label in enumerate(ranked_labels):
        if label >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def set_prf(predicted: set[str], gold: set[str]) -> tuple[float, float, float]:
    """Micro precision/recall/F1 for one example (case-insensitive)."""
    p = {x.lower() for x in predicted}
    g = {x.lower() for x in gold}
    tp = len(p & g)
    precision = tp / len(p) if p else (1.0 if not g else 0.0)
    recall = tp / len(g) if g else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def micro_prf(pairs: Sequence[tuple[set[str], set[str]]]) -> dict[str, float]:
    tp = fp = fn = 0
    for predicted, gold in pairs:
        p = {x.lower() for x in predicted}
        g = {x.lower() for x in gold}
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def mean(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None
