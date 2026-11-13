"""Dense vector semantic retriever using embedding similarity."""

from __future__ import annotations

from collections.abc import Sequence

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.intelligence.providers.base import EmbeddingProviderProtocol
from amara.intelligence.providers.rule_based import DeterministicRuleEmbeddingProvider
from amara.retrieval.types import NormalizedQuery, ScoredMemoryCandidate
from amara.storage.vector_math import cosine_similarity


class SemanticRetriever:
    """Retrieves memory records matching dense semantic embeddings."""

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_provider: EmbeddingProviderProtocol | None = None,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider or DeterministicRuleEmbeddingProvider()

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Query repository with dense embedding vector and compute semantic relevance."""
        # 1. Generate query embedding
        query_vector = await self.embedding_provider.embed_text(query.normalized_text)

        # 2. Query repository using vector constraint
        spec = QuerySpec(
            filter=query_filter,
            query_vector=query_vector,
            top_k=max(top_k * 2, 20),
            include_tombstoned=False,
        )
        records = await self.repository.query(spec)

        # 3. Score and rank candidates
        scored_candidates: list[ScoredMemoryCandidate] = []
        for rec in records:
            if rec.embedding is not None and len(rec.embedding) == len(query_vector):
                raw_sim = cosine_similarity(query_vector, rec.embedding)
                sim_score = max(0.0, min(1.0, float(raw_sim)))
            else:
                sim_score = 0.0

            scored_candidates.append(
                ScoredMemoryCandidate(
                    record=rec,
                    score=sim_score,
                    semantic_score=sim_score,
                    match_explanation=f"Semantic similarity score: {sim_score:.4f}",
                )
            )

        scored_candidates.sort(key=lambda c: c.score, reverse=True)
        return scored_candidates[:top_k]
