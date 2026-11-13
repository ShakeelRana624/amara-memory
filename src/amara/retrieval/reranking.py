"""Cognitive multi-factor reranking engine."""

from __future__ import annotations

import datetime
import math
from collections.abc import Sequence

from amara.enums import LifecycleStatus
from amara.retrieval.types import NormalizedQuery, RerankWeights, ScoredMemoryCandidate


class MemoryReranker:
    """Reranks candidate memories combining retrieval relevance, salience, recency, and utility."""

    def __init__(
        self,
        default_weights: RerankWeights | None = None,
        decay_half_life_days: float = 30.0,
    ) -> None:
        self.weights = default_weights or RerankWeights()
        self.decay_lambda = math.log(2.0) / max(decay_half_life_days, 1.0)

    def rerank(
        self,
        candidates: Sequence[ScoredMemoryCandidate],
        query: NormalizedQuery,
        weights: RerankWeights | None = None,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Apply multi-factor cognitive reranking to candidate memories.

        Note: Relevance score represents query matching quality and is strictly
        separated from factual confidence.
        """
        w = weights or self.weights
        ref_time = query.reference_time or query.valid_at or datetime.datetime.now(datetime.UTC)

        reranked: list[ScoredMemoryCandidate] = []

        for cand in candidates:
            rec = cand.record

            # 1. Base retrieval relevance score (from semantic/lexical/temporal match)
            s_rel = cand.score

            # 2. Intrinsic salience / importance
            s_imp = rec.importance

            # 3. Recency score calculation
            t_anchor = rec.temporal.valid_from or rec.temporal.asserted_at
            delta_days = max(0.0, (ref_time - t_anchor).total_seconds() / 86400.0)
            s_rec = math.exp(-self.decay_lambda * delta_days)

            # 4. Usage utility score normalized to [0.0, 1.0]
            s_util = max(0.0, min(1.0, rec.utility_score / 10.0))

            # 5. Composite cognitive score
            composite = (
                (w.relevance * s_rel)
                + (w.importance * s_imp)
                + (w.recency * s_rec)
                + (w.utility * s_util)
            )

            # 6. Status modulation (discount superseded facts unless historical is requested)
            if rec.status == LifecycleStatus.SUPERSEDED and not query.include_historical:
                composite *= 0.20

            final_score = max(0.0, min(1.0, round(composite, 4)))

            explanation = (
                f"Reranked score: {final_score:.4f} [match={s_rel:.3f}, imp={s_imp:.3f}, "
                f"recency={s_rec:.3f}, utility={s_util:.3f}]"
            )
            if rec.status == LifecycleStatus.SUPERSEDED and not query.include_historical:
                explanation += " (superseded penalty: x0.20)"

            reranked.append(
                ScoredMemoryCandidate(
                    record=rec,
                    score=final_score,
                    semantic_score=cand.semantic_score,
                    lexical_score=cand.lexical_score,
                    temporal_score=cand.temporal_score,
                    relational_score=cand.relational_score,
                    recency_score=round(s_rec, 4),
                    match_explanation=explanation,
                )
            )

        reranked.sort(key=lambda c: c.score, reverse=True)
        return reranked
