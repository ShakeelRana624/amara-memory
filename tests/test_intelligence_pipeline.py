"""Integration test suite for the AMARA memory intelligence and ingestion pipeline."""

from __future__ import annotations

import datetime
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus, MemoryCategory, ProvenanceSourceType, RelationType
from amara.exceptions import MemoryValidationError, ProviderError
from amara.intelligence.pipeline import MemoryIngestionPipeline
from amara.intelligence.providers.mock_llm import MockLLMExtractionProvider
from amara.storage.database import DatabaseManager
from amara.storage.memory import InMemoryMemoryRepository
from amara.storage.postgres import PostgresMemoryRepository

TEST_DB_URL = "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"


@pytest.fixture
def memory_repo() -> MemoryRepository:
    """Provide a thread-safe in-memory repository for fast isolated unit testing."""
    return InMemoryMemoryRepository()


@pytest.fixture
async def pg_repo() -> AsyncGenerator[PostgresMemoryRepository, None]:
    """Provide a PostgresMemoryRepository against live PostgreSQL for end-to-end integration."""
    manager = DatabaseManager(TEST_DB_URL, pool_size=5)
    await manager.initialize()

    # Clean test tables
    async with manager.session() as session:
        await session.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        await session.execute(
            text(
                "TRUNCATE TABLE memory_events, memory_version_history, "
                "memory_relationships, memory_records CASCADE;"
            )
        )

    repo = PostgresMemoryRepository(manager)
    yield repo
    await manager.close()


# ===========================================================================
# End-to-End Ingestion & Modality Routing Tests
# ===========================================================================


async def test_pipeline_ingest_semantic_preference(memory_repo: MemoryRepository) -> None:
    """Verify ingestion of user preference results in structured semantic memory with provenance."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)
    raw_text = "User prefers dark mode in the IDE."

    result = await pipeline.ingest_text(
        content=raw_text,
        tenant_id="tenant-alpha",
        source_id="session-user-01",
        author_id="user-42",
        source_type=ProvenanceSourceType.USER_INPUT,
    )

    assert len(result.stored_records) == 1
    assert result.deduplicated_count == 0
    assert len(result.contradictions_detected) == 0

    record = result.stored_records[0]
    assert record.tenant_id == "tenant-alpha"
    assert record.memory_type == MemoryCategory.SEMANTIC
    assert record.confidence >= 0.90
    assert record.importance >= 0.60
    assert record.source.author_id == "user-42"
    assert record.source.content_hash is not None
    assert len(record.evidence) == 1
    assert "User prefers dark mode" in (record.evidence[0].raw_payload or "")

    # Verify extracted facts attached to metadata
    facts = record.metadata.get("facts", [])
    assert len(facts) >= 1
    assert facts[0]["predicate"] == "prefers"
    assert facts[0]["object"] == "dark mode"


async def test_pipeline_ingest_procedural_workflow(memory_repo: MemoryRepository) -> None:
    """Verify ingestion of multi-step procedure routes to PROCEDURAL modality."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)
    text = (
        "# Build Procedure\n"
        "1. Install uv package manager\n"
        "2. Run ruff check on codebase\n"
        "3. Execute pytest test suite\n"
    )

    result = await pipeline.ingest_text(
        content=text,
        tenant_id="tenant-alpha",
        source_id="runbook-01",
        author_id="devops",
        source_type=ProvenanceSourceType.SYSTEM_INSTRUCTION,
    )

    assert len(result.stored_records) == 1
    record = result.stored_records[0]
    assert record.memory_type == MemoryCategory.PROCEDURAL
    assert record.importance >= 0.70
    assert "skills" in record.metadata
    assert len(record.metadata["skills"][0]["steps"]) == 3


async def test_pipeline_ingest_episodic_narrative(memory_repo: MemoryRepository) -> None:
    """Verify ingestion of narrative events routes to EPISODIC modality."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)
    text = "Yesterday user Alice ran the benchmark suite at 14:00."

    result = await pipeline.ingest_text(
        content=text,
        tenant_id="tenant-alpha",
        source_id="session-102",
        author_id="agent",
        source_type=ProvenanceSourceType.AGENT_REASONING,
    )

    assert len(result.stored_records) == 1
    record = result.stored_records[0]
    assert record.memory_type == MemoryCategory.EPISODIC


# ===========================================================================
# Deduplication Tests
# ===========================================================================


async def test_pipeline_deduplication_exact_content_hash(memory_repo: MemoryRepository) -> None:
    """Verify identical text ingestion is detected as duplicate and reinforces existing record."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)
    text = "User prefers dark mode in the editor."

    # First ingestion: new record stored
    res1 = await pipeline.ingest_text(
        content=text,
        tenant_id="tenant-alpha",
        source_id="sess-1",
        author_id="user-1",
    )
    assert len(res1.stored_records) == 1
    first_id = res1.stored_records[0].id

    # Second ingestion with same content: deduplicated and reinforced
    res2 = await pipeline.ingest_text(
        content="   User prefers dark mode in the editor.   \n",
        tenant_id="tenant-alpha",
        source_id="sess-2",
        author_id="user-1",
    )
    assert len(res2.stored_records) == 0
    assert res2.deduplicated_count == 1
    assert first_id in res2.reinforced_records

    # Verify original record metrics were reinforced
    reloaded = await memory_repo.get_memory("tenant-alpha", first_id)
    assert reloaded is not None
    assert reloaded.access_count == 1
    assert reloaded.utility_score > 0.0


# ===========================================================================
# Contradiction Detection & Historical Fact Preservation Tests
# ===========================================================================


async def test_pipeline_contradiction_detection_temporal_supersede(
    memory_repo: MemoryRepository,
) -> None:
    """Verify contradictory incoming fact supersedes older fact while preserving historical truth."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)

    # 1. Historical Fact asserted at T1: "User prefers light mode."
    t1 = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)
    res1 = await pipeline.ingest_text(
        content="User prefers light mode.",
        tenant_id="tenant-alpha",
        source_id="sess-old",
        author_id="user-1",
        valid_from=t1,
    )
    assert len(res1.stored_records) == 1
    old_record = res1.stored_records[0]
    assert old_record.status == LifecycleStatus.ACTIVE

    # 2. Incoming Contradictory Fact asserted at T2 (now): "User prefers dark mode."
    res2 = await pipeline.ingest_text(
        content="User prefers dark mode.",
        tenant_id="tenant-alpha",
        source_id="sess-new",
        author_id="user-1",
        valid_from=datetime.datetime.now(datetime.UTC),
    )

    # Verify contradiction was detected
    assert len(res2.contradictions_detected) == 1
    conflict = res2.contradictions_detected[0]
    assert conflict.existing_memory_id == old_record.id
    assert conflict.entity == "User"
    assert conflict.attribute == "prefers"
    assert conflict.existing_value == "light mode"
    assert conflict.incoming_value == "dark mode"
    assert conflict.severity == "temporal_evolution"
    assert conflict.temporal_relationship == "supersedes"

    # Verify historical fact was NOT deleted, but transitioned to SUPERSEDED
    reloaded_old = await memory_repo.get_memory("tenant-alpha", old_record.id)
    assert reloaded_old is not None
    assert reloaded_old.status == LifecycleStatus.SUPERSEDED

    # Verify relational graph edge CONTRADICTS was created
    relationships = await memory_repo.get_relationships("tenant-alpha", old_record.id)
    assert len(relationships) == 1
    assert relationships[0].relation_type == RelationType.CONTRADICTS
    assert relationships[0].bidirectional is True


async def test_pipeline_unresolved_contradiction_preserved_for_review(
    memory_repo: MemoryRepository,
) -> None:
    """Verify conflicting facts with simultaneous/ambiguous validity are preserved for review."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)
    t_same = datetime.datetime.now(datetime.UTC)

    # Fact 1: Server runs on port 8000
    res1 = await pipeline.ingest_text(
        content="Backend runs on port 8000.",
        tenant_id="tenant-alpha",
        source_id="config-a",
        author_id="worker-a",
        asserted_at=t_same,
        valid_from=t_same,
    )
    rec1 = res1.stored_records[0]

    # Fact 2 (concurrent from another source): Backend runs on port 9000
    res2 = await pipeline.ingest_text(
        content="Backend runs on port 9000.",
        tenant_id="tenant-alpha",
        source_id="config-b",
        author_id="worker-b",
        asserted_at=t_same,
        valid_from=t_same,
    )
    rec2 = res2.stored_records[0]

    # Both records must be preserved
    assert await memory_repo.get_memory("tenant-alpha", rec1.id) is not None
    assert await memory_repo.get_memory("tenant-alpha", rec2.id) is not None

    # Contradiction flagged for review
    assert len(res2.contradictions_detected) == 1
    assert res2.contradictions_detected[0].status == "review_required"


# ===========================================================================
# Provider Failure Resilience & Error Handling Tests
# ===========================================================================


async def test_pipeline_provider_failure_graceful_fallback(memory_repo: MemoryRepository) -> None:
    """Verify that when primary provider fails, pipeline gracefully falls back to rule-based engine."""
    failing_provider = MockLLMExtractionProvider(
        should_fail=True, failure_message="Remote LLM API timeout"
    )

    pipeline = MemoryIngestionPipeline(
        repository=memory_repo,
        intelligence_provider=failing_provider,
        enable_fallback_on_provider_error=True,
    )

    # Ingestion should still succeed via fallback
    result = await pipeline.ingest_text(
        content="User prefers dark mode.",
        tenant_id="tenant-alpha",
        source_id="sess-fallback",
        author_id="user-1",
    )
    assert len(result.stored_records) == 1
    assert result.stored_records[0].memory_type == MemoryCategory.SEMANTIC


async def test_pipeline_provider_failure_explicit_error_mode(
    memory_repo: MemoryRepository,
) -> None:
    """Verify that when fallback is disabled, provider failures raise ProviderError cleanly."""
    failing_provider = MockLLMExtractionProvider(
        should_fail=True, failure_message="Service Unavailable"
    )

    pipeline = MemoryIngestionPipeline(
        repository=memory_repo,
        intelligence_provider=failing_provider,
        enable_fallback_on_provider_error=False,
    )

    with pytest.raises(ProviderError) as exc_info:
        await pipeline.ingest_text(
            content="User prefers dark mode.",
            tenant_id="tenant-alpha",
            source_id="sess-err",
            author_id="user-1",
        )
    assert "Service Unavailable" in str(exc_info.value)


# ===========================================================================
# Validation Rejection Tests
# ===========================================================================


async def test_pipeline_empty_input_rejection(memory_repo: MemoryRepository) -> None:
    """Verify empty or whitespace-only inputs are rejected with MemoryValidationError."""
    pipeline = MemoryIngestionPipeline(repository=memory_repo)

    with pytest.raises(MemoryValidationError):
        await pipeline.ingest_text(
            content="   \n\t   ",
            tenant_id="tenant-alpha",
            source_id="sess-err",
            author_id="user-1",
        )


# ===========================================================================
# End-to-End Execution with Live PostgreSQL Storage Engine
# ===========================================================================


async def test_pipeline_with_live_postgresql(pg_repo: PostgresMemoryRepository) -> None:
    """Verify full end-to-end ingestion pipeline operating against real PostgreSQL 16 + pgvector."""
    pipeline = MemoryIngestionPipeline(repository=pg_repo)

    # 1. Ingest initial preference
    res1 = await pipeline.ingest_text(
        content="User prefers dark mode in the developer console.",
        tenant_id="tenant-postgres",
        source_id="session-pg-01",
        author_id="user-42",
    )
    assert len(res1.stored_records) == 1
    first_id = res1.stored_records[0].id

    # Verify in PostgreSQL
    pg_record = await pg_repo.get_memory("tenant-postgres", first_id)
    assert pg_record is not None
    assert pg_record.normalized_content == "User prefers dark mode in the developer console."
    assert len(pg_record.embedding or []) == 1536

    # 2. Ingest duplicate -> triggers reinforcement in PostgreSQL
    res2 = await pipeline.ingest_text(
        content="User prefers dark mode in the developer console.",
        tenant_id="tenant-postgres",
        source_id="session-pg-02",
        author_id="user-42",
    )
    assert len(res2.stored_records) == 0
    assert res2.deduplicated_count == 1
    assert first_id in res2.reinforced_records

    reloaded = await pg_repo.get_memory("tenant-postgres", first_id)
    assert reloaded is not None
    assert reloaded.access_count == 1
