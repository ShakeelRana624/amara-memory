"""Integration test suite for AMARA PostgreSQL 16+ storage engine with pgvector and RLS."""

from __future__ import annotations

import datetime
import pathlib
from collections.abc import AsyncGenerator, Sequence
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from amara.contracts.query import QueryFilter, QuerySpec
from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    MemoryEventType,
    ProvenanceSourceType,
    RelationType,
)
from amara.exceptions import (
    DuplicateMemoryError,
    InvalidMemoryStateError,
    MemoryNotFoundError,
    RepositoryError,
    StorageConnectionError,
)
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity
from amara.storage.database import DatabaseManager
from amara.storage.postgres import PostgresMemoryRepository

TEST_DB_URL = "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"


def make_vector(val: float, dim: int = 1536) -> list[float]:
    """Generate a normalized 1536-dimensional vector for testing."""
    vec = [0.0] * dim
    vec[0] = val
    vec[1] = 1.0 - val
    return vec


def make_test_record(
    tenant_id: str = "tenant-test-a",
    namespace: str = "default",
    memory_type: MemoryCategory = MemoryCategory.EPISODIC,
    content: str = "User prefers dark mode in the IDE.",
    embedding: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
    version: int = 1,
    valid_from: datetime.datetime | None = None,
    valid_to: datetime.datetime | None = None,
    parent_ids: Sequence[UUID] = (),
    root_id: UUID | None = None,
) -> MemoryRecord:
    """Helper to construct a fully validated MemoryRecord for integration testing."""
    now = datetime.datetime.now(datetime.UTC)
    rec_id = uuid4()
    return MemoryRecord(
        id=rec_id,
        root_id=root_id or rec_id,
        tenant_id=tenant_id,
        namespace=namespace,
        memory_type=memory_type,
        status=LifecycleStatus.ACTIVE,
        original_content=content,
        normalized_content=content.strip().lower(),
        source=MemorySource(
            source_id="session-101",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="user-42",
            session_id="sess-xyz",
            content_hash="0" * 64,
        ),
        confidence=0.95,
        importance=0.8,
        temporal=TemporalValidity(
            asserted_at=now,
            valid_from=valid_from or (now - datetime.timedelta(hours=1)),
            valid_to=valid_to,
        ),
        version=version,
        parent_ids=tuple(parent_ids),
        embedding=embedding,
        embedding_model_id="text-embedding-3-small" if embedding else None,
        metadata=metadata or {"topic": "ui_preferences", "tested": True},
        evidence=(
            MemoryEvidence(
                evidence_id=uuid4(),
                source_reference="session-101",
                raw_payload=content,
                confidence_score=0.98,
            ),
        ),
    )


@pytest.fixture
async def db_manager() -> AsyncGenerator[DatabaseManager, None]:
    """Initialize a DatabaseManager and clean up tables for each test."""
    manager = DatabaseManager(TEST_DB_URL, pool_size=5, max_overflow=5)
    await manager.initialize()

    # Clean test tables with bypass_rls enabled for cleanup
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
def repo(db_manager: DatabaseManager) -> PostgresMemoryRepository:
    """Provide a PostgresMemoryRepository instance bound to the active test database."""
    return PostgresMemoryRepository(db_manager)


# ===========================================================================
# DatabaseManager & Connection Pool Tests
# ===========================================================================


async def test_database_manager_health(db_manager: DatabaseManager) -> None:
    """Verify that DatabaseManager performs active pre-ping health checks."""
    is_healthy = await db_manager.check_health()
    assert is_healthy is True


async def test_database_manager_connection_failure() -> None:
    """Verify that invalid connection endpoints raise StorageConnectionError."""
    bad_manager = DatabaseManager(
        "postgresql+asyncpg://amara:wrongpassword@127.0.0.1:5432/amara_test",
        pool_timeout=1.0,
    )
    with pytest.raises(StorageConnectionError):
        await bad_manager.initialize(max_retries=1, retry_delay=0.1)
    await bad_manager.close()


async def test_database_manager_empty_tenant_validation(db_manager: DatabaseManager) -> None:
    """Verify that passing an empty tenant string to session context raises ValueError."""
    with pytest.raises(ValueError, match="tenant_id cannot be empty or whitespace"):
        async with db_manager.session(tenant_id="   "):
            pass


# ===========================================================================
# Memory CRUD & Integrity Tests
# ===========================================================================


async def test_create_and_get_memory(repo: PostgresMemoryRepository) -> None:
    """Verify successful insertion and exact retrieval of a MemoryRecord."""
    rec = make_test_record(tenant_id="tenant-alpha", content="Python 3.12 is the primary runtime.")
    created = await repo.create_memory(rec)
    assert created.id == rec.id

    fetched = await repo.get_memory("tenant-alpha", rec.id)
    assert fetched is not None
    assert fetched.id == rec.id
    assert fetched.tenant_id == "tenant-alpha"
    assert fetched.original_content == "Python 3.12 is the primary runtime."
    assert fetched.confidence == 0.95
    assert fetched.importance == 0.8
    assert fetched.source.author_id == "user-42"
    assert fetched.metadata["topic"] == "ui_preferences"
    assert len(fetched.evidence) == 1
    assert fetched.evidence[0].raw_payload == "Python 3.12 is the primary runtime."


async def test_duplicate_memory_error(repo: PostgresMemoryRepository) -> None:
    """Verify that persisting a duplicate memory ID raises DuplicateMemoryError."""
    rec = make_test_record(tenant_id="tenant-alpha")
    await repo.create_memory(rec)

    with pytest.raises(DuplicateMemoryError) as exc_info:
        await repo.create_memory(rec)
    assert exc_info.value.memory_id == str(rec.id)


async def test_get_nonexistent_memory(repo: PostgresMemoryRepository) -> None:
    """Verify get_memory returns None when memory ID is not found."""
    non_existent = uuid4()
    result = await repo.get_memory("tenant-alpha", non_existent)
    assert result is None


async def test_store_batch_atomic(repo: PostgresMemoryRepository) -> None:
    """Verify storing multiple records in batch across tenants."""
    records = [
        make_test_record(tenant_id="tenant-alpha", content=f"Batch memory item {i}")
        for i in range(5)
    ]
    await repo.store_batch(records)

    count = await repo.count("tenant-alpha")
    assert count == 5


# ===========================================================================
# Optimistic Concurrency & Audit Version History Tests
# ===========================================================================


async def test_update_memory_with_version_history(repo: PostgresMemoryRepository) -> None:
    """Verify controlled update, optimistic locking, and version history capture."""
    rec = make_test_record(tenant_id="tenant-alpha", content="Initial state of memory.")
    await repo.create_memory(rec)
    assert rec.version == 1

    # Execute valid update
    updated = await repo.update_memory(
        tenant_id="tenant-alpha",
        memory_id=rec.id,
        expected_version=1,
        content="Refined state of memory.",
        status=LifecycleStatus.CONSOLIDATED,
        metadata={"editor": "agent-orchestrator", "refinements": 1},
        changed_by="agent-orchestrator",
        change_reason="Knowledge consolidation pipeline",
    )

    assert updated.version == 2
    assert updated.original_content == "Refined state of memory."
    assert updated.status == LifecycleStatus.CONSOLIDATED
    assert updated.metadata["editor"] == "agent-orchestrator"

    # Verify version history snapshot was persisted
    history = await repo.get_memory_history("tenant-alpha", rec.id)
    assert len(history) == 1
    v1_snapshot = history[0]
    assert v1_snapshot["version"] == 1
    assert v1_snapshot["original_content"] == "Initial state of memory."
    assert v1_snapshot["status"] == LifecycleStatus.ACTIVE.value
    assert v1_snapshot["changed_by"] == "agent-orchestrator"
    assert v1_snapshot["change_reason"] == "Knowledge consolidation pipeline"

    # Verify domain events recorded
    events = await repo.get_memory_events("tenant-alpha", rec.id)
    event_types = [e.event_type for e in events]
    assert MemoryEventType.CREATED in event_types
    assert MemoryEventType.UPDATED in event_types


async def test_update_memory_optimistic_concurrency_conflict(
    repo: PostgresMemoryRepository,
) -> None:
    """Verify optimistic concurrency conflict raises error when version mismatches."""
    rec = make_test_record(tenant_id="tenant-alpha", content="Base content.")
    await repo.create_memory(rec)

    # First worker updates version from 1 -> 2
    await repo.update_memory(
        tenant_id="tenant-alpha",
        memory_id=rec.id,
        expected_version=1,
        content="Worker 1 update.",
    )

    # Second worker attempts update with stale version 1
    with pytest.raises(InvalidMemoryStateError) as exc_info:
        await repo.update_memory(
            tenant_id="tenant-alpha",
            memory_id=rec.id,
            expected_version=1,
            content="Worker 2 conflict.",
        )
    assert "Optimistic lock conflict" in str(exc_info.value)


async def test_update_memory_illegal_lifecycle_transition(repo: PostgresMemoryRepository) -> None:
    """Verify illegal lifecycle transitions are rejected by the state machine."""
    rec = make_test_record(tenant_id="tenant-alpha")
    await repo.create_memory(rec)

    # Soft delete to TOMBSTONED
    await repo.delete_memory("tenant-alpha", rec.id, hard=False)

    # Attempt illegal transition: TOMBSTONED cannot transition to ACTIVE
    with pytest.raises(InvalidMemoryStateError):
        await repo.update_memory(
            tenant_id="tenant-alpha",
            memory_id=rec.id,
            expected_version=1,
            status=LifecycleStatus.ACTIVE,
        )


# ===========================================================================
# Deletion Semantics (Soft Tombstone vs. Hard Cascade)
# ===========================================================================


async def test_soft_delete_lifecycle(repo: PostgresMemoryRepository) -> None:
    """Verify soft deletion marks record as TOMBSTONED and excludes from default queries."""
    rec = make_test_record(tenant_id="tenant-alpha", content="Temporary scratch memory.")
    await repo.create_memory(rec)

    del_count = await repo.delete_memory("tenant-alpha", rec.id, hard=False)
    assert del_count == 1

    # Record still exists in storage but status is TOMBSTONED
    stored = await repo.get_memory("tenant-alpha", rec.id)
    assert stored is not None
    assert stored.status == LifecycleStatus.TOMBSTONED

    # Excluded from active count
    active_count = await repo.count("tenant-alpha")
    assert active_count == 0

    # Excluded from default list_memories
    memories = await repo.list_memories("tenant-alpha")
    assert len(memories) == 0

    # Present when explicitly asking for TOMBSTONED
    tombstoned = await repo.list_memories("tenant-alpha", statuses=[LifecycleStatus.TOMBSTONED])
    assert len(tombstoned) == 1
    assert tombstoned[0].id == rec.id


async def test_hard_delete_cascade_derivation(repo: PostgresMemoryRepository) -> None:
    """Verify hard delete cascades to orphan children but preserves multi-parent children."""
    # 1. Create root ancestor A
    rec_a = make_test_record(tenant_id="tenant-alpha", content="Root observation A.")
    await repo.create_memory(rec_a)

    # 2. Create another independent root D
    rec_d = make_test_record(tenant_id="tenant-alpha", content="Independent root D.")
    await repo.create_memory(rec_d)

    # 3. Create child B derived solely from A
    rec_b = make_test_record(
        tenant_id="tenant-alpha",
        content="Derived child B.",
        parent_ids=[rec_a.id],
        root_id=rec_a.id,
    )
    await repo.create_memory(rec_b)

    # 4. Create child C derived from both A and D
    rec_c = make_test_record(
        tenant_id="tenant-alpha",
        content="Synthesized child C.",
        parent_ids=[rec_a.id, rec_d.id],
        root_id=rec_a.id,
    )
    await repo.create_memory(rec_c)

    # 5. Hard delete root A with cascade=True
    purged_total = await repo.delete_memory("tenant-alpha", rec_a.id, hard=True, cascade=True)
    # rec_a and rec_b (orphan) should be purged: 2 records total
    assert purged_total == 2

    # Verify rec_a and rec_b no longer exist
    assert await repo.get_memory("tenant-alpha", rec_a.id) is None
    assert await repo.get_memory("tenant-alpha", rec_b.id) is None

    # Verify rec_c survived because root D still exists, with rec_a pruned from parent_ids
    child_c = await repo.get_memory("tenant-alpha", rec_c.id)
    assert child_c is not None
    assert rec_a.id not in child_c.parent_ids
    assert rec_d.id in child_c.parent_ids


# ===========================================================================
# Relational Graph Associations
# ===========================================================================


async def test_relationships_and_bidirectional_traversal(repo: PostgresMemoryRepository) -> None:
    """Verify creating and retrieving relational links between memory records."""
    rec_a = make_test_record(tenant_id="tenant-alpha", content="Server running on port 8000.")
    rec_b = make_test_record(tenant_id="tenant-alpha", content="Server running on port 9000.")
    await repo.create_memory(rec_a)
    await repo.create_memory(rec_b)

    rel = MemoryRelationship(
        relationship_id=uuid4(),
        tenant_id="tenant-alpha",
        source_id=rec_a.id,
        target_id=rec_b.id,
        relation_type=RelationType.CONTRADICTS,
        weight=0.95,
        bidirectional=True,
        metadata={"detected_by": "contradiction_engine"},
    )
    await repo.create_relationship(rel)

    # Outgoing traversal from A
    edges_from_a = await repo.get_relationships("tenant-alpha", rec_a.id)
    assert len(edges_from_a) == 1
    assert edges_from_a[0].relation_type == RelationType.CONTRADICTS

    # Bidirectional incoming traversal from B
    edges_from_b = await repo.get_relationships("tenant-alpha", rec_b.id)
    assert len(edges_from_b) == 1
    assert edges_from_b[0].source_id == rec_a.id


async def test_relationship_integrity_foreign_key(repo: PostgresMemoryRepository) -> None:
    """Verify creating a relationship with non-existent memories raises RepositoryError."""
    rel = MemoryRelationship(
        relationship_id=uuid4(),
        tenant_id="tenant-alpha",
        source_id=uuid4(),
        target_id=uuid4(),
        relation_type=RelationType.DEPENDS_ON,
    )
    with pytest.raises(RepositoryError):
        await repo.create_relationship(rel)


# ===========================================================================
# Metadata Search & Cognitive Metrics
# ===========================================================================


async def test_search_metadata_jsonb_containment(repo: PostgresMemoryRepository) -> None:
    """Verify JSONB deep containment metadata search."""
    rec1 = make_test_record(
        tenant_id="tenant-alpha",
        metadata={"config": {"theme": "dark", "fontSize": 14}},
    )
    rec2 = make_test_record(
        tenant_id="tenant-alpha",
        metadata={"config": {"theme": "light", "fontSize": 14}},
    )
    await repo.create_memory(rec1)
    await repo.create_memory(rec2)

    # Search for dark theme
    dark_matches = await repo.search_metadata("tenant-alpha", ["config", "theme"], "dark")
    assert len(dark_matches) == 1
    assert dark_matches[0].id == rec1.id


async def test_update_cognitive_metrics(repo: PostgresMemoryRepository) -> None:
    """Verify reinforcement of access count and utility scores."""
    rec = make_test_record(tenant_id="tenant-alpha")
    await repo.create_memory(rec)
    assert rec.access_count == 0
    assert rec.utility_score == 0.0

    now = datetime.datetime.now(datetime.UTC)
    await repo.update_metrics(
        tenant_id="tenant-alpha",
        memory_id=rec.id,
        utility_delta=0.75,
        accessed_at=now,
    )

    reloaded = await repo.get_memory("tenant-alpha", rec.id)
    assert reloaded is not None
    assert reloaded.access_count == 1
    assert pytest.approx(reloaded.utility_score) == 0.75
    assert reloaded.last_accessed_at is not None


# ===========================================================================
# Dense Vector Search (pgvector HNSW Cosine Distance)
# ===========================================================================


async def test_vector_similarity_search_pgvector(repo: PostgresMemoryRepository) -> None:
    """Verify that vector queries retrieve nearest neighbors ranked by cosine distance."""
    # Target query vector
    query_vec = make_vector(1.0)

    # Close match (val = 0.9)
    close_rec = make_test_record(
        tenant_id="tenant-alpha",
        content="Artificial intelligence and memory architecture.",
        embedding=make_vector(0.9),
    )
    # Distant match (val = 0.1)
    distant_rec = make_test_record(
        tenant_id="tenant-alpha",
        content="Gardening and tomato cultivation tips.",
        embedding=make_vector(0.1),
    )

    await repo.create_memory(close_rec)
    await repo.create_memory(distant_rec)

    spec = QuerySpec(
        filter=QueryFilter(tenant_id="tenant-alpha"),
        query_vector=query_vec,
        top_k=2,
    )
    results = await repo.query(spec)

    assert len(results) == 2
    assert results[0].id == close_rec.id
    assert results[1].id == distant_rec.id


# ===========================================================================
# Multi-Tenant Isolation Strictness
# ===========================================================================


async def test_tenant_isolation_strictness(repo: PostgresMemoryRepository) -> None:
    """Verify that Tenant A cannot view, update, query, or delete records belonging to Tenant B."""
    rec_a = make_test_record(
        tenant_id="tenant-alpha",
        content="Confidential strategy for Alpha Corp.",
        metadata={"sec": "high"},
    )
    rec_b = make_test_record(
        tenant_id="tenant-beta",
        content="Proprietary roadmap for Beta Corp.",
        metadata={"sec": "high"},
    )

    await repo.create_memory(rec_a)
    await repo.create_memory(rec_b)

    # 1. get_memory isolation
    assert await repo.get_memory("tenant-alpha", rec_b.id) is None
    assert await repo.get_memory("tenant-beta", rec_a.id) is None

    # 2. list_memories isolation
    list_a = await repo.list_memories("tenant-alpha")
    assert len(list_a) == 1
    assert list_a[0].id == rec_a.id

    # 3. search_metadata isolation
    sec_a = await repo.search_metadata("tenant-alpha", ["sec"], "high")
    assert len(sec_a) == 1
    assert sec_a[0].id == rec_a.id

    # 4. update_memory isolation
    with pytest.raises(MemoryNotFoundError):
        await repo.update_memory(
            tenant_id="tenant-alpha",
            memory_id=rec_b.id,
            expected_version=1,
            content="Tampered content",
        )

    # 5. delete_memory isolation
    with pytest.raises(MemoryNotFoundError):
        await repo.delete_memory("tenant-alpha", rec_b.id, hard=True)

    # 6. query vector isolation
    vec = make_vector(0.5)
    query_results = await repo.query(
        QuerySpec(
            filter=QueryFilter(tenant_id="tenant-alpha"),
            query_vector=vec,
            top_k=10,
        )
    )
    assert all(r.tenant_id == "tenant-alpha" for r in query_results)


# ===========================================================================
# Alembic Migration Lifecycle Verification
# ===========================================================================


def test_alembic_migrations_lifecycle() -> None:
    """Verify programmatic Alembic schema downgrade and re-upgrade execution."""
    root_dir = pathlib.Path(__file__).parent.parent
    ini_path = root_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(root_dir / "migrations"))

    # Test downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Test re-upgrade to head
    command.upgrade(alembic_cfg, "head")


# ===========================================================================
# Query Filtering, Lexical Search & Modality Edge Cases
# ===========================================================================


async def test_postgres_repo_lifecycle_init_and_close() -> None:
    """Verify repo.initialize() and repo.close() manage underlying engine and schema."""
    mgr = DatabaseManager(TEST_DB_URL, pool_size=2)
    custom_repo = PostgresMemoryRepository(mgr)
    await custom_repo.initialize()
    assert await mgr.check_health() is True
    await custom_repo.close()


async def test_database_manager_uninitialized_health() -> None:
    """Verify check_health returns False when DatabaseManager is uninitialized."""
    mgr = DatabaseManager(TEST_DB_URL)
    assert await mgr.check_health() is False
    with pytest.raises(StorageConnectionError):
        _ = mgr.engine
    with pytest.raises(StorageConnectionError):
        async with mgr.session():
            pass


async def test_database_manager_idempotent_initialize(db_manager: DatabaseManager) -> None:
    """Verify initialize() can be called multiple times safely."""
    await db_manager.initialize()
    assert await db_manager.check_health() is True


async def test_store_batch_empty(repo: PostgresMemoryRepository) -> None:
    """Verify store_batch handles empty record sequences safely."""
    await repo.store_batch([])


async def test_list_memories_advanced_filters(repo: PostgresMemoryRepository) -> None:
    """Verify list_memories filtering by namespace, memory_types, and validity timestamp."""
    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)
    future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)

    rec1 = make_test_record(
        tenant_id="tenant-filter",
        namespace="agents",
        memory_type=MemoryCategory.PROCEDURAL,
        content="Workflow step 1: compile code.",
        valid_from=past,
        valid_to=future,
    )
    rec2 = make_test_record(
        tenant_id="tenant-filter",
        namespace="scratch",
        memory_type=MemoryCategory.EPISODIC,
        content="Transient thought.",
        valid_from=past,
        valid_to=past + datetime.timedelta(hours=1),
    )
    await repo.create_memory(rec1)
    await repo.create_memory(rec2)

    # Filter by namespace
    agent_mems = await repo.list_memories("tenant-filter", namespace="agents")
    assert len(agent_mems) == 1
    assert agent_mems[0].id == rec1.id

    # Count by namespace
    agent_count = await repo.count("tenant-filter", namespace="agents")
    assert agent_count == 1

    # Filter by memory category
    procedural = await repo.list_memories("tenant-filter", memory_types=[MemoryCategory.PROCEDURAL])
    assert len(procedural) == 1
    assert procedural[0].id == rec1.id

    # Filter by validity timestamp (now is inside rec1's window, but outside rec2's window)
    valid_now = await repo.list_memories(
        "tenant-filter", valid_at=datetime.datetime.now(datetime.UTC)
    )
    assert len(valid_now) == 1
    assert valid_now[0].id == rec1.id


async def test_update_status_direct(repo: PostgresMemoryRepository) -> None:
    """Verify update_status mutates lifecycle status directly."""
    rec = make_test_record(tenant_id="tenant-alpha")
    await repo.create_memory(rec)

    await repo.update_status("tenant-alpha", rec.id, LifecycleStatus.DECAYING)
    reloaded = await repo.get_memory("tenant-alpha", rec.id)
    assert reloaded is not None
    assert reloaded.status == LifecycleStatus.DECAYING

    # Attempt updating status of non-existent record raises MemoryNotFoundError
    with pytest.raises(MemoryNotFoundError):
        await repo.update_status("tenant-alpha", uuid4(), LifecycleStatus.ACTIVE)


async def test_update_metrics_nonexistent(repo: PostgresMemoryRepository) -> None:
    """Verify updating metrics on non-existent record raises MemoryNotFoundError."""
    with pytest.raises(MemoryNotFoundError):
        await repo.update_metrics(
            "tenant-alpha",
            uuid4(),
            utility_delta=0.5,
            accessed_at=datetime.datetime.now(datetime.UTC),
        )


async def test_composite_query_lexical_and_filters(repo: PostgresMemoryRepository) -> None:
    """Verify composite query with lexical search, confidence bounds, and metadata filters."""
    rec = make_test_record(
        tenant_id="tenant-query",
        namespace="production",
        content="PostgreSQL vector indexing optimizes semantic nearest-neighbor search.",
        metadata={"category": "database", "priority": "high"},
    )
    await repo.create_memory(rec)

    # 1. Lexical search matching "nearest-neighbor"
    spec = QuerySpec(
        filter=QueryFilter(
            tenant_id="tenant-query",
            namespace="production",
            metadata_filter={"priority": "high"},
        ),
        query_text="nearest-neighbor",
        min_confidence=0.9,
        min_importance=0.5,
    )
    matches = await repo.query(spec)
    assert len(matches) == 1
    assert matches[0].id == rec.id

    # 2. Lexical search mismatch
    no_matches = await repo.query(
        QuerySpec(
            filter=QueryFilter(tenant_id="tenant-query"),
            query_text="unrelated keyword",
        )
    )
    assert len(no_matches) == 0
