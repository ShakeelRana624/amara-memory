"""Temporal and bi-temporal validity-aware memory retriever."""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.retrieval.types import NormalizedQuery, ScoredMemoryCandidate


class TemporalRetriever:
    """Retrieves and scores memories based on temporal validity and recency decay."""

    def __init__(
        self,
        repository: MemoryRepository,
        decay_half_life_days: float = 30.0,
    ) -> None:
        self.repository = repository
        self.decay_lambda = math.log(2.0) / max(decay_half_life_days, 1.0)

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Fetch records within temporal constraints and calculate temporal relevance scores."""
        ref_time = query.valid_at or query.reference_time or datetime.datetime.now(datetime.UTC)

        # 1. Fetch records matching filter
        spec = QuerySpec(
            filter=query_filter,
            top_k=max(top_k * 3, 30),
            include_tombstoned=False,
        )
        records = await self.repository.query(spec)

        scored: list[ScoredMemoryCandidate] = []
        for rec in records:
            # 1. Bi-temporal validity evaluation
            is_currently_valid = rec.is_valid_at(ref_time)
            validity_score = 1.0 if is_currently_valid else 0.20

            # 2. Time range bounds check
            if query.time_range is not None:
                start, end = query.time_range
                t_anchor = rec.temporal.valid_from
                if start is not None and t_anchor < start:
                    continue
                if end is not None and t_anchor > end:
                    continue

            # 3. Recency decay calculation
            t_event = rec.temporal.valid_from or rec.temporal.asserted_at
            delta_days = max(0.0, (ref_time - t_event).total_seconds() / 86400.0)
            recency = math.exp(-self.decay_lambda * delta_days)

            # 4. Composite temporal score
            composite = round(0.50 * validity_score + 0.50 * recency, 4)

            scored.append(
                ScoredMemoryCandidate(
                    record=rec,
                    score=composite,
                    temporal_score=composite,
                    recency_score=round(recency, 4),
                    match_explanation=(
                        f"Temporal validity: {is_currently_valid}, "
                        f"recency: {recency:.3f} (delta: {delta_days:.1f}d)"
                    ),
                )
            )

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]
