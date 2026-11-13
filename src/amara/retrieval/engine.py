"""High-level facade and orchestrator for AMARA memory retrieval."""

from __future__ import annotations

import datetime
import time
from collections.abc import Sequence

from amara.contracts.query import QueryFilter
from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus, MemoryCategory
from amara.exceptions import TenantIsolationError
from amara.intelligence.providers.base import EmbeddingProviderProtocol
from amara.intelligence.providers.rule_based import DeterministicRuleEmbeddingProvider
from amara.retrieval.query_analyzer import QueryAnalyzer
from amara.retrieval.reranking import MemoryReranker
from amara.retrieval.retrievers.hybrid import HybridRetriever
from amara.retrieval.retrievers.lexical import LexicalRetriever
from amara.retrieval.retrievers.relational import RelationalRetriever
from amara.retrieval.retrievers.semantic import SemanticRetriever
from amara.retrieval.retrievers.temporal import TemporalRetriever
from amara.retrieval.types import (
    MemorySearchResult,
    RetrievalResponse,
    RetrievalStrategy,
    RetrievalWeights,
    ScoredMemoryCandidate,
)


class MemoryRetrievalEngine:
    """Production-grade hybrid memory retrieval engine orchestrating multi-channel search."""

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_provider: EmbeddingProviderProtocol | None = None,
        decay_half_life_days: float = 30.0,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider or DeterministicRuleEmbeddingProvider()
        self.query_analyzer = QueryAnalyzer()

        self.semantic_retriever = SemanticRetriever(
            repository=self.repository,
            embedding_provider=self.embedding_provider,
        )
        self.lexical_retriever = LexicalRetriever(repository=self.repository)
        self.temporal_retriever = TemporalRetriever(
            repository=self.repository,
            decay_half_life_days=decay_half_life_days,
        )
        self.relational_retriever = RelationalRetriever(repository=self.repository)

        self.hybrid_retriever = HybridRetriever(
            semantic=self.semantic_retriever,
            lexical=self.lexical_retriever,
            temporal=self.temporal_retriever,
            relational=self.relational_retriever,
        )
        self.reranker = MemoryReranker(decay_half_life_days=decay_half_life_days)

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        namespace: str = "default",
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        top_k: int = 10,
        min_score: float = 0.0,
        memory_types: Sequence[MemoryCategory] | None = None,
        valid_at: datetime.datetime | None = None,
        reference_time: datetime.datetime | None = None,
        time_range: tuple[datetime.datetime | None, datetime.datetime | None] | None = None,
        include_historical: bool = False,
        weights: RetrievalWeights | None = None,
        rerank: bool = True,
    ) -> RetrievalResponse:
        """Execute multi-channel retrieval matching the query, tenant, and strategy."""
        start_time = time.perf_counter()

        # 1. Enforce strict tenant isolation
        clean_tenant = tenant_id.strip() if tenant_id else ""
        if not clean_tenant:
            raise TenantIsolationError(clean_tenant, "tenant_id cannot be empty or whitespace.")

        clean_namespace = namespace.strip() if namespace else "default"

        # 2. Decompose and normalize query
        norm_query = await self.query_analyzer.analyze(
            query=query,
            reference_time=reference_time,
            valid_at=valid_at,
            time_range=time_range,
            include_historical=include_historical,
        )

        # 3. Assemble repository query filter
        statuses = (
            (
                LifecycleStatus.ACTIVE,
                LifecycleStatus.DECAYING,
                LifecycleStatus.SUPERSEDED,
            )
            if norm_query.include_historical
            else (LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING)
        )
        q_filter = QueryFilter(
            tenant_id=clean_tenant,
            namespace=clean_namespace,
            memory_types=memory_types,
            statuses=statuses,
            reference_time=norm_query.reference_time,
            valid_at=norm_query.valid_at,
        )

        # 4. Dispatch retrieval strategy
        candidates: Sequence[ScoredMemoryCandidate] = ()

        if strategy == RetrievalStrategy.SEMANTIC:
            candidates = await self.semantic_retriever.retrieve(
                norm_query, q_filter, top_k=top_k * 2
            )
        elif strategy == RetrievalStrategy.LEXICAL:
            candidates = await self.lexical_retriever.retrieve(
                norm_query, q_filter, top_k=top_k * 2
            )
        elif strategy == RetrievalStrategy.TEMPORAL:
            candidates = await self.temporal_retriever.retrieve(
                norm_query, q_filter, top_k=top_k * 2
            )
        elif strategy == RetrievalStrategy.RELATIONAL:
            candidates = await self.relational_retriever.retrieve(
                norm_query, q_filter, top_k=top_k * 2
            )
        else:
            # Default to HYBRID retrieval
            candidates = await self.hybrid_retriever.retrieve(
                norm_query, q_filter, top_k=top_k * 2, weights=weights
            )

        # 5. Optional cognitive multi-factor reranking
        if rerank and candidates:
            candidates = self.reranker.rerank(candidates, norm_query)

        # 6. Hydrate relevant relationships and format results
        results: list[MemorySearchResult] = []
        for cand in candidates:
            if cand.score < min_score:
                continue

            rec = cand.record
            # Hydrate actual graph relationships from repository (never fabricated)
            relationships = await self.repository.get_relationships(clean_tenant, rec.id)

            results.append(
                MemorySearchResult(
                    memory_id=rec.id,
                    memory_type=rec.memory_type,
                    content=rec.original_content,
                    normalized_content=rec.normalized_content,
                    source_id=rec.source.source_id,
                    author_id=rec.source.author_id,
                    timestamp=rec.temporal.valid_from or rec.temporal.asserted_at,
                    confidence=rec.confidence,
                    importance=rec.importance,
                    relevance_score=cand.score,
                    temporal_validity=rec.temporal,
                    lifecycle_status=rec.status,
                    relevant_relationships=relationships,
                    evidence=rec.evidence,
                    metadata=rec.metadata,
                    match_explanation=cand.match_explanation,
                )
            )

            if len(results) >= top_k:
                break

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        return RetrievalResponse(
            query=query,
            strategy=strategy,
            intent=norm_query.intent,
            results=tuple(results),
            total_candidates=len(candidates),
            latency_ms=elapsed_ms,
            tenant_id=clean_tenant,
            namespace=clean_namespace,
        )
