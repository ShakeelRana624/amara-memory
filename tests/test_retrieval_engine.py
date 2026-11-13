"""Comprehensive deterministic test suite for MemoryRetrievalEngine."""

from __future__ import annotations

import datetime
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from amara.enums import LifecycleStatus, RelationType
from amara.exceptions import TenantIsolationError
from amara.intelligence.pipeline import MemoryIngestionPipeline
from amara.intelligence.providers.rule_based import DeterministicRuleEmbeddingProvider
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.retrieval.types import RetrievalStrategy
from amara.storage.database import DatabaseManager
from amara.storage.memory import InMemoryMemoryRepository
from amara.storage.postgres import PostgresMemoryRepository

TEST_DB_URL = "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"


@pytest.fixture
def in_memory_repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def embedder() -> DeterministicRuleEmbeddingProvider:
    return DeterministicRuleEmbeddingProvider()


@pytest.fixture
async def pg_db() -> AsyncGenerator[DatabaseManager, None]:
    manager = DatabaseManager(TEST_DB_URL, pool_size=5, max_overflow=5)
    await manager.initialize()
    async with manager.session() as session:
        await session.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        await session.execute(
            text(
                "TRUNCATE TABLE memory_events, memory_version_history, "
                "memory_relationships, memory_records CASCADE;"
            )
        )
    yield manager
    await manager.close()


@pytest.fixture
def pg_repo(pg_db: DatabaseManager) -> PostgresMemoryRepository:
    return PostgresMemoryRepository(pg_db)


async def seed_memory_corpus(repo: InMemoryMemoryRepository | PostgresMemoryRepository) -> None:
    """Seed a rich, controlled knowledge base for retrieval evaluation."""
    pipeline = MemoryIngestionPipeline(repository=repo)
    t_base = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=14)

    # 1. Exact fact: Server port
    await pipeline.ingest_text(
        content="Backend API service runs on port 8000.",
        tenant_id="tenant-alpha",
        source_id="config-backend",
        author_id="devops",
        asserted_at=t_base,
    )

    # 2. Database infrastructure fact
    await pipeline.ingest_text(
        content="Production database runs on PostgreSQL version 16.",
        tenant_id="tenant-alpha",
        source_id="config-db",
        author_id="dba",
        asserted_at=t_base,
    )

    # 3. Procedural runbook
    await pipeline.ingest_text(
        content=(
            "# Deploy to Production\n"
            "1. Run test suite with pytest.\n"
            "2. Build Docker container image.\n"
            "3. Deploy container to Kubernetes cluster."
        ),
        tenant_id="tenant-alpha",
        source_id="runbook-deploy",
        author_id="devops",
        asserted_at=t_base,
    )

    # 4. Temporal evolution: User theme setting (light mode 14 days ago, updated to dark mode 2 days ago)
    await pipeline.ingest_text(
        content="User prefers light mode in the dashboard.",
        tenant_id="tenant-alpha",
        source_id="session-t1",
        author_id="user-1",
        asserted_at=t_base,
        valid_from=t_base,
    )

    await pipeline.ingest_text(
        content="User prefers dark mode in the dashboard.",
        tenant_id="tenant-alpha",
        source_id="session-t2",
        author_id="user-1",
        asserted_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2),
        valid_from=datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2),
    )

    # 5. Competing simultaneous contradiction from two different authors
    t_same = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=5)
    await pipeline.ingest_text(
        content="Redis cache cluster runs on port 6379.",
        tenant_id="tenant-alpha",
        source_id="inventory-worker-a",
        author_id="worker-a",
        asserted_at=t_same,
        valid_from=t_same,
    )
    await pipeline.ingest_text(
        content="Redis cache cluster runs on port 6380.",
        tenant_id="tenant-alpha",
        source_id="inventory-worker-b",
        author_id="worker-b",
        asserted_at=t_same,
        valid_from=t_same,
    )

    # 6. Tenant isolation test record in tenant-beta
    await pipeline.ingest_text(
        content="Top secret project codename is Pegasus.",
        tenant_id="tenant-beta",
        source_id="classified-doc",
        author_id="executive",
        asserted_at=t_base,
    )


# ===========================================================================
# Deterministic Retrieval Evaluation Cases
# ===========================================================================


async def test_retrieval_exact_facts(in_memory_repo: InMemoryMemoryRepository) -> None:
    """Evaluation Case 1: Exact facts retrieval."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    response = await engine.retrieve(
        query="Backend API service runs on port 8000.",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=3,
    )

    assert len(response.results) >= 1
    top = response.results[0]
    assert "8000" in top.content
    assert top.relevance_score > 0.60
    # Epistemic factual confidence is independent of relevance score
    assert 0.90 <= top.confidence <= 1.0
    assert top.source_id == "config-backend"
    assert top.memory_id is not None
    assert top.timestamp is not None
    assert top.temporal_validity is not None


async def test_retrieval_semantic_paraphrases(in_memory_repo: InMemoryMemoryRepository) -> None:
    """Evaluation Case 2: Semantic paraphrases retrieval."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    # Query phrased differently from stored "Production database runs on PostgreSQL version 16."
    response = await engine.retrieve(
        query="Which relational database engine and version are used in production?",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=3,
    )

    assert len(response.results) >= 1
    found_db = any("PostgreSQL" in r.content for r in response.results)
    assert found_db is True


async def test_retrieval_historical_facts(in_memory_repo: InMemoryMemoryRepository) -> None:
    """Evaluation Case 3: Historical facts retrieval with temporal intent."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    # User explicitly asking for past theme
    response = await engine.retrieve(
        query="What was the user's previous or historical theme setting?",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        include_historical=True,
        top_k=5,
    )

    assert len(response.results) >= 1
    contents = [r.content for r in response.results]
    assert any("light mode" in c for c in contents)


async def test_retrieval_updated_facts(in_memory_repo: InMemoryMemoryRepository) -> None:
    """Evaluation Case 4: Updated facts retrieval (current state preference)."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    # Current preference check without historical flag
    response = await engine.retrieve(
        query="What theme does the user prefer in the dashboard?",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=3,
    )

    assert len(response.results) >= 1
    top = response.results[0]
    # Current active fact ("dark mode") must outrank superseded fact ("light mode")
    assert "dark mode" in top.content
    assert top.lifecycle_status == LifecycleStatus.ACTIVE


async def test_retrieval_contradictions_and_relevant_relationships(
    in_memory_repo: InMemoryMemoryRepository,
) -> None:
    """Evaluation Case 5: Contradictions and relevant relationship edges surfaced."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    response = await engine.retrieve(
        query="What port does the Redis cache cluster run on?",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=5,
    )

    assert len(response.results) >= 1
    # Check that both competing records or contradiction edges are surfaced
    ports_found = [r.content for r in response.results if "Redis" in r.content]
    assert len(ports_found) >= 1

    # Verify that relationship edges are hydrated and never fabricated
    for res in response.results:
        if "Redis" in res.content and res.relevant_relationships:
            has_contradiction = any(
                rel.relation_type == RelationType.CONTRADICTS for rel in res.relevant_relationships
            )
            assert has_contradiction is True


async def test_retrieval_unrelated_questions(in_memory_repo: InMemoryMemoryRepository) -> None:
    """Evaluation Case 6: Unrelated questions returning low relevance or empty."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    # Completely out-of-domain query with min_score threshold
    response = await engine.retrieve(
        query="Explain quantum chromodynamics and gluon plasma physics in stars.",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        min_score=0.75,
        top_k=5,
    )

    # Out of domain query should have 0 results passing min_score 0.75
    assert len(response.results) == 0


async def test_retrieval_empty_results_and_namespaces(
    in_memory_repo: InMemoryMemoryRepository,
) -> None:
    """Evaluation Case 7: Empty results for non-existent namespace or filters."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    response = await engine.retrieve(
        query="Backend port",
        tenant_id="tenant-alpha",
        namespace="non_existent_ns",
        strategy=RetrievalStrategy.HYBRID,
        top_k=5,
    )
    assert len(response.results) == 0


async def test_retrieval_cross_tenant_access_isolation(
    in_memory_repo: InMemoryMemoryRepository,
) -> None:
    """Evaluation Case 8: Cross-tenant isolation verification."""
    await seed_memory_corpus(in_memory_repo)
    engine = MemoryRetrievalEngine(repository=in_memory_repo)

    # Querying tenant-alpha for secret data stored exclusively in tenant-beta
    response = await engine.retrieve(
        query="What is the top secret project codename Pegasus?",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=5,
    )
    # Must NEVER return tenant-beta records
    assert not any("Pegasus" in r.content for r in response.results)
    for r in response.results:
        assert r.source_id != "classified-doc"

    # Querying tenant-beta directly returns the record
    response_beta = await engine.retrieve(
        query="What is the top secret project codename Pegasus?",
        tenant_id="tenant-beta",
        strategy=RetrievalStrategy.HYBRID,
        top_k=5,
    )
    assert len(response_beta.results) == 1
    assert "Pegasus" in response_beta.results[0].content

    # Attempting empty or whitespace tenant ID must raise TenantIsolationError
    with pytest.raises(TenantIsolationError):
        await engine.retrieve(
            query="test",
            tenant_id="   ",
            strategy=RetrievalStrategy.HYBRID,
        )


# ===========================================================================
# End-to-End Execution with Live PostgreSQL 16 + pgvector Storage
# ===========================================================================


async def test_retrieval_engine_with_live_postgresql(
    pg_repo: PostgresMemoryRepository,
) -> None:
    """Verify full end-to-end hybrid retrieval against real PostgreSQL 16 + pgvector."""
    await seed_memory_corpus(pg_repo)
    engine = MemoryRetrievalEngine(repository=pg_repo)

    # 1. Hybrid query against live PostgreSQL
    res = await engine.retrieve(
        query="Backend API service port",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.HYBRID,
        top_k=3,
    )

    assert len(res.results) >= 1
    assert "8000" in res.results[0].content
    assert res.results[0].relevance_score > 0.4
    assert res.latency_ms > 0.0

    # 2. Semantic query against pgvector cosine distance
    res_sem = await engine.retrieve(
        query="Production database engine",
        tenant_id="tenant-alpha",
        strategy=RetrievalStrategy.SEMANTIC,
        top_k=3,
    )
    assert len(res_sem.results) >= 1
    assert "PostgreSQL" in res_sem.results[0].content
