"""Standardized information retrieval and cognitive memory evaluation metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence


def recall_at_k(retrieved_ids: Sequence[str], ground_truth_ids: Sequence[str], k: int) -> float:
    """Compute Recall@K: proportion of relevant memories retrieved within top K candidates."""
    if not ground_truth_ids:
        return 1.0 if not retrieved_ids else 0.0

    top_k = retrieved_ids[:k]
    hits = sum(1 for target in ground_truth_ids if target in top_k)
    return float(hits / len(ground_truth_ids))


def precision_at_k(retrieved_ids: Sequence[str], ground_truth_ids: Sequence[str], k: int) -> float:
    """Compute Precision@K: proportion of top K retrieved candidates that are relevant."""
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for item in top_k if item in ground_truth_ids)
    return float(hits / min(k, len(top_k)))


def mean_reciprocal_rank(retrieved_ids: Sequence[str], ground_truth_ids: Sequence[str]) -> float:
    """Compute Reciprocal Rank: inverse rank position of the first relevant candidate."""
    if not ground_truth_ids:
        return 1.0 if not retrieved_ids else 0.0

    for rank, item in enumerate(retrieved_ids, start=1):
        if item in ground_truth_ids:
            return 1.0 / float(rank)
    return 0.0


def ndcg_at_k(
    retrieved_ids: Sequence[str], ground_truth_relevance: dict[str, float], k: int
) -> float:
    """Compute Normalized Discounted Cumulative Gain (nDCG@K)."""
    top_k = retrieved_ids[:k]
    if not top_k or not ground_truth_relevance:
        return 0.0

    # Calculate DCG
    dcg = 0.0
    for rank, item in enumerate(top_k, start=1):
        rel = ground_truth_relevance.get(item, 0.0)
        dcg += (2.0**rel - 1.0) / math.log2(rank + 1)

    # Calculate Ideal DCG (IDCG)
    sorted_rels = sorted(ground_truth_relevance.values(), reverse=True)[:k]
    idcg = 0.0
    for rank, rel in enumerate(sorted_rels, start=1):
        idcg += (2.0**rel - 1.0) / math.log2(rank + 1)

    if idcg <= 0.0:
        return 0.0
    return float(dcg / idcg)


def factual_answer_accuracy(context_text: str, ground_truth_tokens: Sequence[str]) -> float:
    """Evaluate whether verified ground-truth tokens/facts exist within prompt context."""
    if not ground_truth_tokens:
        return 1.0
    text_lower = context_text.lower()
    matches = sum(1 for token in ground_truth_tokens if token.lower() in text_lower)
    return float(matches / len(ground_truth_tokens))


def temporal_accuracy(
    retrieved_content: Sequence[str],
    current_valid_content: str,
    stale_content: str | None = None,
) -> float:
    """Check whether retrieved context surfaces the temporally valid fact vs the superseded stale fact."""
    joined = " ".join(retrieved_content).lower()
    current_present = current_valid_content.lower() in joined
    stale_present = stale_content.lower() in joined if stale_content else False

    if current_present and not stale_present:
        return 1.0
    if current_present and stale_present:
        return 0.5  # Partial: both returned, requiring LLM disambiguation
    return 0.0


def abstention_accuracy(
    should_abstain: bool,
    did_abstain: bool,
) -> float:
    """Evaluate abstention correctness when memory is absent or queries are out-of-scope."""
    return 1.0 if should_abstain == did_abstain else 0.0
