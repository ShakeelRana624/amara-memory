"""Vector mathematics utilities for in-memory cosine similarity and distance calculation.

Implemented with standard library math to maintain zero external dependencies.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Compute cosine similarity between two dense vectors.

    Returns a float in the range [-1.0, 1.0]. Returns 0.0 if either vector has zero magnitude.
    Raises ValueError if vectors have mismatched dimensions.
    """
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimension mismatch: len(v1)={len(v1)} != len(v2)={len(v2)}.")

    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for a, b in zip(v1, v2, strict=True):
        dot_product += a * b
        norm_a += a * a
        norm_b += b * b

    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0

    similarity = dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))
    # Clamp to avoid floating point imprecision beyond [-1.0, 1.0]
    return max(-1.0, min(1.0, similarity))


def euclidean_distance(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Compute Euclidean (L2) distance between two dense vectors."""
    if len(v1) != len(v2):
        raise ValueError(f"Vector dimension mismatch: len(v1)={len(v1)} != len(v2)={len(v2)}.")

    sum_sq = sum((a - b) ** 2 for a, b in zip(v1, v2, strict=True))
    return math.sqrt(sum_sq)
