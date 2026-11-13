"""Tests validating each retrieval method independently and in hybrid combination."""

from __future__ import annotations

import datetime
from uuid import uuid4

import pytest

from amara.contracts.query import QueryFilter
from amara.enums import LifecycleStatus, MemoryCategory, ProvenanceSourceType, RelationType
from amara.intelligence.providers.rule_based import DeterministicRuleEmbeddingProvider
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity
from amara.retrieval.query_analyzer import QueryAnalyzer
from amara.retrieval.reranking import MemoryReranker
from amara.retrieval.retrievers.hybrid import HybridRetriever
from amara.retrieval.retrievers.lexical import LexicalRetriever
from amara.retrieval.retrievers.relational import RelationalRetriever
from amara.retrieval.retrievers.semantic import SemanticRetriever
from amara.retrieval.retrievers.temporal import TemporalRetriever
from amara.retrieval.types import (
    NormalizedQuery,
    RetrievalWeights,
    ScoredMemoryCandidate,
)
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def memory_repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def embedder() -> DeterministicRuleEmbeddingProvider:
    return DeterministicRuleEmbeddingProvider()


@pytest.fixture
def analyzer() -> QueryAnalyzer:
    return QueryAnalyzer()


async def make_test_record(
    content: str,
    embedder: DeterministicRuleEmbeddingProvider,
    tenant_id: str = "tenant-alpha",
    namespace: str = "default",
    category: MemoryCategory = MemoryCategory.SEMANTIC,
    valid_from: datetime.datetime | None = None,
    valid_to: datetime.datetime | None = None,
    status: LifecycleStatus = LifecycleStatus.ACTIVE,
    importance: float = 0.5,
    utility_score: float = 0.0,
) -> MemoryRecord:
    now = datetime.datetime.now(datetime.UTC)
    vec = await embedder.embed_text(content)
    rid = uuid4()
    return MemoryRecord(
        id=rid,
        root_id=rid,
        tenant_id=tenant_id,
        namespace=namespace,
        memory_type=category,
        status=status,
        original_content=content,
        normalized_content=content.strip().lower(),
        source=MemorySource(
            source_id="test-source",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="test-author",
            content_hash="h" * 64,
        ),
        confidence=0.95,
        importance=importance,
        temporal=TemporalValidity(
            asserted_at=valid_from or now,
            valid_from=valid_from or now,
            valid_to=valid_to,
        ),
        embedding=vec,
        embedding_model_id=embedder.model_id,
        utility_score=utility_score,
        evidence=(
            MemoryEvidence(
                evidence_id=uuid4(),
                source_reference="test-source",
                raw_payload=content,
                confidence_score=0.95,
            ),
        ),
    )


# ===========================================================================
# 1. Semantic Vector Retrieval Tests
# ===========================================================================


async def test_semantic_retriever_ranking(
    memory_repo: InMemoryMemoryRepository,
    embedder: DeterministicRuleEmbeddingProvider,
    analyzer: QueryAnalyzer,
) -> None:
    """Verify semantic vector retrieval ranks highest for semantically aligned content."""
    rec_match = await make_test_record("PostgreSQL database server runs on port 5432.", embedder)
    rec_other = await make_test_record("User Alice prefers dark mode theme.", embedder)
    await memory_repo.create_memory(rec_match)
    await memory_repo.create_memory(rec_other)

    retriever = SemanticRetriever(repository=memory_repo, embedding_provider=embedder)
    q = await analyzer.analyze("PostgreSQL database port")
    q_filter = QueryFilter(tenant_id="tenant-alpha")

    results = await retriever.retrieve(q, q_filter, top_k=5)
    assert len(results) == 2
    assert results[0].record.id == rec_match.id
    assert results[0].semantic_score > results[1].semantic_score


# ===========================================================================
# 2. Lexical Keyword Retrieval Tests
# ===========================================================================


async def test_lexical_retriever_exact_phrase_and_keywords(
    memory_repo: InMemoryMemoryRepository,
    embedder: DeterministicRuleEmbeddingProvider,
    analyzer: QueryAnalyzer,
) -> None:
    """Verify lexical retriever awards exact phrase match and keyword token overlaps."""
    rec1 = await make_test_record("Redis cache is running on port 6379.", embedder)
    rec2 = await make_test_record("Backend API service is deployed on port 8000.", embedder)
    await memory_repo.create_memory(rec1)
    await memory_repo.create_memory(rec2)

    retriever = LexicalRetriever(repository=memory_repo)
    q = await analyzer.analyze("Redis cache port 6379")
    q_filter = QueryFilter(tenant_id="tenant-alpha")

    results = await retriever.retrieve(q, q_filter, top_k=5)
    assert len(results) > 0
    assert results[0].record.id == rec1.id
    assert results[0].lexical_score > 0.5


# ===========================================================================
# 3. Temporal Retrieval Tests
# ===========================================================================


async def test_temporal_retriever_recency_and_validity(
    memory_repo: InMemoryMemoryRepository,
    embedder: DeterministicRuleEmbeddingProvider,
    analyzer: QueryAnalyzer,
) -> None:
    """Verify temporal retriever ranks recent facts higher and enforces validity intervals."""
    t_now = datetime.datetime.now(datetime.UTC)
    t_old = t_now - datetime.timedelta(days=90)

    rec_recent = await make_test_record("Current team sprint goal.", embedder, valid_from=t_now)
    rec_old = await make_test_record("Old project roadmap Q1.", embedder, valid_from=t_old)
    await memory_repo.create_memory(rec_recent)
    await memory_repo.create_memory(rec_old)

    retriever = TemporalRetriever(repository=memory_repo, decay_half_life_days=30.0)
    q = await analyzer.analyze("Sprint roadmap goals")
    q_filter = QueryFilter(tenant_id="tenant-alpha")

    results = await retriever.retrieve(q, q_filter, top_k=5)
    assert len(results) == 2
    assert results[0].record.id == rec_recent.id
    assert results[0].recency_score > results[1].recency_score


# ===========================================================================
# 4. Relational Graph Retrieval Tests
# ===========================================================================


async def test_relational_retriever_graph_edge_discovery(
    memory_repo: InMemoryMemoryRepository,
    embedder: DeterministicRuleEmbeddingProvider,
    analyzer: QueryAnalyzer,
) -> None:
    """Verify relational retriever discovers connected memories across CONTRADICTS and DEPENDS_ON edges."""
    rec_seed = await make_test_record("PostgreSQL production database.", embedder)
    rec_connected = await make_test_record("Database backup replica configuration.", embedder)
    await memory_repo.create_memory(rec_seed)
    await memory_repo.create_memory(rec_connected)

    edge = MemoryRelationship(
        source_id=rec_seed.id,
        target_id=rec_connected.id,
        relation_type=RelationType.DEPENDS_ON,
        tenant_id="tenant-alpha",
        weight=0.9,
    )
    await memory_repo.create_relationship(edge)

    retriever = RelationalRetriever(repository=memory_repo, max_hops=1)
    q = await analyzer.analyze("PostgreSQL production database")
    q_filter = QueryFilter(tenant_id="tenant-alpha")

    results = await retriever.retrieve(q, q_filter, top_k=5)
    assert len(results) >= 1
    target_ids = [r.record.id for r in results]
    assert rec_connected.id in target_ids


# ===========================================================================
# 5. Hybrid Retrieval & Reranker Tests
# ===========================================================================


async def test_hybrid_retriever_multi_channel_fusion(
    memory_repo: InMemoryMemoryRepository,
    embedder: DeterministicRuleEmbeddingProvider,
    analyzer: QueryAnalyzer,
) -> None:
    """Verify hybrid retriever merges multiple channels with configurable weights."""
    rec1 = await make_test_record("User Alice prefers dark mode in IDE.", embedder)
    rec2 = await make_test_record("User Bob uses light mode in terminal.", embedder)
    await memory_repo.create_memory(rec1)
    await memory_repo.create_memory(rec2)

    hybrid = HybridRetriever(
        semantic=SemanticRetriever(memory_repo, embedder),
        lexical=LexicalRetriever(memory_repo),
        temporal=TemporalRetriever(memory_repo),
        relational=RelationalRetriever(memory_repo),
    )

    q = await analyzer.analyze("Alice dark mode preference")
    q_filter = QueryFilter(tenant_id="tenant-alpha")

    custom_weights = RetrievalWeights(semantic=0.4, lexical=0.4, temporal=0.1, relational=0.1)
    results = await hybrid.retrieve(q, q_filter, top_k=5, weights=custom_weights)

    assert len(results) >= 1
    assert results[0].record.id == rec1.id
    assert results[0].semantic_score > 0.0
    assert results[0].lexical_score > 0.0


def test_reranker_superseded_fact_penalty() -> None:
    """Verify reranker discounts superseded historical memories unless explicitly requested."""
    reranker = MemoryReranker()
    now = datetime.datetime.now(datetime.UTC)

    rec_active = MemoryRecord(
        id=uuid4(),
        root_id=uuid4(),
        tenant_id="tenant-alpha",
        namespace="default",
        memory_type=MemoryCategory.SEMANTIC,
        status=LifecycleStatus.ACTIVE,
        original_content="Active preference: dark mode",
        normalized_content="active preference: dark mode",
        source=MemorySource(
            source_id="s1",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="user-1",
            content_hash="1" * 64,
        ),
        confidence=0.95,
        importance=0.8,
        temporal=TemporalValidity(asserted_at=now, valid_from=now),
    )

    rec_superseded = MemoryRecord(
        id=uuid4(),
        root_id=uuid4(),
        tenant_id="tenant-alpha",
        namespace="default",
        memory_type=MemoryCategory.SEMANTIC,
        status=LifecycleStatus.SUPERSEDED,
        original_content="Old preference: light mode",
        normalized_content="old preference: light mode",
        source=MemorySource(
            source_id="s2",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="user-1",
            content_hash="2" * 64,
        ),
        confidence=0.95,
        importance=0.8,
        temporal=TemporalValidity(
            asserted_at=now - datetime.timedelta(days=10),
            valid_from=now - datetime.timedelta(days=10),
        ),
    )

    cand_active = ScoredMemoryCandidate(record=rec_active, score=0.85)
    cand_super = ScoredMemoryCandidate(record=rec_superseded, score=0.85)

    # Standard query (not historical)
    q_normal = NormalizedQuery(
        original_text="theme", normalized_text="theme", include_historical=False
    )
    reranked = reranker.rerank([cand_super, cand_active], q_normal)

    assert reranked[0].record.id == rec_active.id
    assert reranked[1].score < (reranked[0].score * 0.5)

    # Historical query (include_historical=True)
    q_hist = NormalizedQuery(
        original_text="past theme", normalized_text="past theme", include_historical=True
    )
    reranked_hist = reranker.rerank([cand_super, cand_active], q_hist)
    # No 80% penalty when historical is requested
    assert reranked_hist[0].score > 0.4
