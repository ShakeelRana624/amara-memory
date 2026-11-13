"""Integration test suite for AMARA Lifecycle Management and Context Reconstruction on PostgreSQL 16."""

from __future__ import annotations

import datetime
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from amara.context.engine import ContextReconstructionEngine
from amara.context.types import ContextBudget
from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
)
from amara.lifecycle.manager import MemoryLifecycleManager
from amara.models.record import MemoryRecord
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.storage.database import DatabaseManager
from amara.storage.postgres import PostgresMemoryRepository

TEST_DB_URL = "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"


@pytest.fixture
async def db_manager() -> AsyncGenerator[DatabaseManager, None]:
    """Initialize a DatabaseManager and truncate test tables."""
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
def postgres_repo(db_manager: DatabaseManager) -> PostgresMemoryRepository:
    return PostgresMemoryRepository(db_manager)


@pytest.fixture
def lifecycle_mgr(postgres_repo: PostgresMemoryRepository) -> MemoryLifecycleManager:
    return MemoryLifecycleManager(repository=postgres_repo)


@pytest.fixture
def context_engine(postgres_repo: PostgresMemoryRepository) -> ContextReconstructionEngine:
    retrieval_engine = MemoryRetrievalEngine(repository=postgres_repo)
    return ContextReconstructionEngine(retrieval_engine=retrieval_engine)


@pytest.mark.asyncio
async def test_postgres_lifecycle_consolidation_flow(
    lifecycle_mgr: MemoryLifecycleManager,
    postgres_repo: PostgresMemoryRepository,
) -> None:
    """Test full consolidation flow against real PostgreSQL database."""
    now = datetime.datetime.now(datetime.UTC)
    tenant_id = "tenant-prod-a"

    # Insert two related episodic memories
    m1 = MemoryRecord.create(
        tenant_id=tenant_id,
        content="Developer configured PostgreSQL connection pooling with pool_size=10.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="dev-1",
        confidence=0.95,
        importance=0.75,
        asserted_at=now - datetime.timedelta(hours=2),
    )
    m2 = MemoryRecord.create(
        tenant_id=tenant_id,
        content="Developer configured PostgreSQL max_overflow=20 for spike traffic.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="dev-2",
        confidence=0.95,
        importance=0.75,
        asserted_at=now - datetime.timedelta(hours=1),
    )

    await postgres_repo.store(m1)
    await postgres_repo.store(m2)

    # Run consolidation cycle
    cycle_res = await lifecycle_mgr.run_lifecycle_cycle(tenant_id=tenant_id)
    assert cycle_res["tenant_id"] == tenant_id

    # Verify both records exist in DB and were not deleted
    db_m1 = await postgres_repo.get_by_id(tenant_id, m1.id)
    db_m2 = await postgres_repo.get_by_id(tenant_id, m2.id)
    assert db_m1 is not None
    assert db_m2 is not None


@pytest.mark.asyncio
async def test_postgres_archive_restore_and_soft_delete(
    lifecycle_mgr: MemoryLifecycleManager,
    postgres_repo: PostgresMemoryRepository,
) -> None:
    """Test archival, restoration, and soft deletion against live PostgreSQL."""
    tenant_id = "tenant-ops"
    record = MemoryRecord.create(
        tenant_id=tenant_id,
        content="Historical configuration setting: maintenance window Sunday 2am.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="admin",
        importance=0.5,
    )
    await postgres_repo.store(record)

    # 1. Archive
    archived = await lifecycle_mgr.archive(tenant_id=tenant_id, memory_id=record.id)
    assert archived.status == LifecycleStatus.ARCHIVED

    db_archived = await postgres_repo.get_by_id(tenant_id, record.id)
    assert db_archived is not None
    assert db_archived.status == LifecycleStatus.ARCHIVED

    # 2. Restore
    restored = await lifecycle_mgr.restore(tenant_id=tenant_id, memory_id=record.id)
    assert restored.status == LifecycleStatus.ACTIVE

    db_restored = await postgres_repo.get_by_id(tenant_id, record.id)
    assert db_restored is not None
    assert db_restored.status == LifecycleStatus.ACTIVE

    # 3. Soft delete
    deleted = await lifecycle_mgr.delete(tenant_id=tenant_id, memory_id=record.id, hard=False)
    assert deleted is True

    db_deleted = await postgres_repo.get_by_id(tenant_id, record.id)
    assert db_deleted is not None
    assert db_deleted.status == LifecycleStatus.TOMBSTONED


@pytest.mark.asyncio
async def test_postgres_context_reconstruction_end_to_end(
    context_engine: ContextReconstructionEngine,
    postgres_repo: PostgresMemoryRepository,
) -> None:
    """Test full context reconstruction retrieving real records from PostgreSQL."""
    now = datetime.datetime.now(datetime.UTC)
    tenant_id = "tenant-reconstruct"

    m1 = MemoryRecord.create(
        tenant_id=tenant_id,
        content="Antigravity pairs pairing software engineers with autonomous cognitive agents.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="researcher",
        confidence=0.99,
        importance=0.90,
        asserted_at=now,
    )
    m2 = MemoryRecord.create(
        tenant_id=tenant_id,
        content="AMARA stands for Adaptive Memory Architecture for Reasoning and AI.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="architect",
        confidence=1.0,
        importance=0.95,
        asserted_at=now,
    )

    await postgres_repo.store(m1)
    await postgres_repo.store(m2)

    result = await context_engine.reconstruct(
        query="What is AMARA and what does it stand for?",
        tenant_id=tenant_id,
        budget=ContextBudget(max_tokens=800, system_reserved_tokens=100),
    )

    assert result.abstention_recommended is False
    assert result.candidates_packed >= 1
    assert len(result.citations) >= 1
    assert "[REF-1]" in result.formatted_context
    assert "AMARA" in result.formatted_context
    assert result.total_tokens_used > 0
    assert result.total_tokens_used <= 800
