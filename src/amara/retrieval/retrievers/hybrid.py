"""Hybrid multi-channel retrieval orchestrator combining multiple search methods."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from uuid import UUID

from amara.contracts.query import QueryFilter
from amara.retrieval.retrievers.lexical import LexicalRetriever
from amara.retrieval.retrievers.relational import RelationalRetriever
from amara.retrieval.retrievers.semantic import SemanticRetriever
from amara.retrieval.retrievers.temporal import TemporalRetriever
from amara.retrieval.types import (
    NormalizedQuery,
    RetrievalWeights,
    ScoredMemoryCandidate,
)


class HybridRetriever:
    """Combines semantic, lexical, temporal, and relational candidate generators."""

    def __init__(
        self,
        semantic: SemanticRetriever,
        lexical: LexicalRetriever,
        temporal: TemporalRetriever,
        relational: RelationalRetriever,
        default_weights: RetrievalWeights | None = None,
    ) -> None:
        self.semantic = semantic
        self.lexical = lexical
        self.temporal = temporal
        self.relational = relational
        self.default_weights = default_weights or RetrievalWeights()

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
        weights: RetrievalWeights | None = None,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Execute parallel multi-channel candidate generation and fuse scores."""
        active_weights = (weights or self.default_weights).normalized()

        # 1. Fetch candidate pools in parallel across all 4 channels
        sem_res, lex_res, temp_res, rel_res = await asyncio.gather(
            self.semantic.retrieve(query, query_filter, top_k=top_k * 2),
            self.lexical.retrieve(query, query_filter, top_k=top_k * 2),
            self.temporal.retrieve(query, query_filter, top_k=top_k * 2),
            self.relational.retrieve(query, query_filter, top_k=top_k * 2),
        )

        # 2. Merge candidate pools by memory ID
        pool: dict[UUID, ScoredMemoryCandidate] = {}

        # Track per-channel scores: {record_id: {channel: score}}
        scores: dict[UUID, dict[str, float]] = {}

        for c in sem_res:
            rid = c.record.id
            pool[rid] = c
            scores.setdefault(rid, {})["sem"] = c.semantic_score

        for c in lex_res:
            rid = c.record.id
            pool[rid] = c
            scores.setdefault(rid, {})["lex"] = c.lexical_score

        for c in temp_res:
            rid = c.record.id
            pool[rid] = c
            scores.setdefault(rid, {})["temp"] = c.temporal_score

        for c in rel_res:
            rid = c.record.id
            pool[rid] = c
            scores.setdefault(rid, {})["rel"] = c.relational_score

        # 3. Calculate fused hybrid score
        fused_candidates: list[ScoredMemoryCandidate] = []
        for rid, base_cand in pool.items():
            ch_scores = scores.get(rid, {})
            s_sem = ch_scores.get("sem", 0.0)
            s_lex = ch_scores.get("lex", 0.0)
            s_temp = ch_scores.get("temp", 0.0)
            s_rel = ch_scores.get("rel", 0.0)

            composite = (
                (active_weights.semantic * s_sem)
                + (active_weights.lexical * s_lex)
                + (active_weights.temporal * s_temp)
                + (active_weights.relational * s_rel)
            )
            composite_score = max(0.0, min(1.0, round(composite, 4)))

            explanation = (
                f"Hybrid fusion: {composite_score:.4f} ["
                f"sem={s_sem:.3f} (w={active_weights.semantic}), "
                f"lex={s_lex:.3f} (w={active_weights.lexical}), "
                f"temp={s_temp:.3f} (w={active_weights.temporal}), "
                f"rel={s_rel:.3f} (w={active_weights.relational})]"
            )

            fused_candidates.append(
                ScoredMemoryCandidate(
                    record=base_cand.record,
                    score=composite_score,
                    semantic_score=s_sem,
                    lexical_score=s_lex,
                    temporal_score=s_temp,
                    relational_score=s_rel,
                    recency_score=base_cand.recency_score,
                    match_explanation=explanation,
                )
            )

        fused_candidates.sort(key=lambda c: c.score, reverse=True)
        return fused_candidates[:top_k]
