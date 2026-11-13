"""Relationship and graph traversal retriever."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar
from uuid import UUID

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import RelationType
from amara.models.record import MemoryRecord
from amara.retrieval.types import NormalizedQuery, ScoredMemoryCandidate


class RelationalRetriever:
    """Traverses relationship graph edges to discover connected knowledge."""

    _RELATION_WEIGHTS: ClassVar[dict[RelationType, float]] = {
        RelationType.CONTRADICTS: 0.95,
        RelationType.DEPENDS_ON: 0.85,
        RelationType.CAUSAL: 0.80,
        RelationType.ENTITY_ATTRIBUTE: 0.75,
        RelationType.ASSOCIATED_WITH: 0.70,
        RelationType.TEMPORAL_NEXT: 0.65,
    }

    def __init__(self, repository: MemoryRepository, max_hops: int = 1) -> None:
        self.repository = repository
        self.max_hops = max(1, min(max_hops, 3))

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Discover connected memory records by traversing association graph edges."""
        tenant_id = query_filter.tenant_id

        # 1. Identify seed memories matching query text or entities
        seed_spec = QuerySpec(
            filter=query_filter,
            query_text=query.normalized_text,
            top_k=5,
            include_tombstoned=False,
        )
        seed_records = await self.repository.query(seed_spec)
        if not seed_records:
            return ()

        # 2. Traverse outward edges from seed memories
        visited_ids: set[UUID] = {s.id for s in seed_records}
        candidate_map: dict[UUID, tuple[MemoryRecord, float, str]] = {}

        for seed in seed_records:
            relationships = await self.repository.get_relationships(tenant_id, seed.id)
            for edge in relationships:
                target_id = edge.target_id if edge.source_id == seed.id else edge.source_id
                if target_id in visited_ids:
                    continue

                visited_ids.add(target_id)
                target_rec = await self.repository.get_memory(tenant_id, target_id)
                if target_rec is None or target_rec.is_tombstoned:
                    continue

                rel_weight = self._RELATION_WEIGHTS.get(edge.relation_type, 0.60)
                path_score = round(min(1.0, edge.weight * rel_weight), 4)
                explanation = (
                    f"Graph edge '{edge.relation_type.value}' connected to seed "
                    f"'{seed.normalized_content[:40]}...' (score: {path_score})"
                )

                if (target_id not in candidate_map) or (path_score > candidate_map[target_id][1]):
                    candidate_map[target_id] = (target_rec, path_score, explanation)

        # 3. Assemble and rank scored candidates
        scored: list[ScoredMemoryCandidate] = [
            ScoredMemoryCandidate(
                record=rec,
                score=score,
                relational_score=score,
                match_explanation=expl,
            )
            for rec, score, expl in candidate_map.values()
        ]

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]
