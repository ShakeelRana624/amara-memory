"""Unit tests for AMARA MemoryLifecycleManager orchestrator."""

from __future__ import annotations

import datetime

import pytest

from amara.enums import LifecycleStatus, MemoryCategory
from amara.lifecycle.manager import MemoryLifecycleManager
from amara.lifecycle.types import ConsolidationPolicy, RetentionPolicy
from amara.models.record import MemoryRecord
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def lifecycle_mgr(repo: InMemoryMemoryRepository) -> MemoryLifecycleManager:
    return MemoryLifecycleManager(
        repository=repo,
        retention_policy=RetentionPolicy(
            decay_half_life_days=30.0,
            auto_archive_expired=True,
            respect_retention_locks=True,
        ),
        consolidation_policy=ConsolidationPolicy(
            similarity_threshold=0.60,
            min_cluster_size=2,
            auto_transition_parents=True,
        ),
    )


@pytest.mark.asyncio
async def test_retain_reinforces_utility_and_reactivates_decaying_record(
    lifecycle_mgr: MemoryLifecycleManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that retain() increments access count, adds utility delta, and reactivates decaying memory."""
    rec = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Important API deployment procedure",
        memory_type=MemoryCategory.PROCEDURAL,
        author_id="user_1",
    )
    # Manually set to decaying
    rec.update_status(LifecycleStatus.DECAYING)
    await repo.store(rec)

    assert rec.status == LifecycleStatus.DECAYING
    assert rec.access_count == 0
    assert rec.utility_score == 0.0

    # Execute retain operation with utility reinforcement
    retained = await lifecycle_mgr.retain(
        tenant_id="tenant_1",
        memory_id=rec.id,
        utility_delta=2.5,
    )

    assert retained.status == LifecycleStatus.ACTIVE
    assert retained.access_count == 1
    assert retained.utility_score == 2.5
    assert retained.last_accessed_at is not None


@pytest.mark.asyncio
async def test_update_controlled_content_and_version(
    lifecycle_mgr: MemoryLifecycleManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test update() increments version and updates normalized content."""
    rec = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Initial draft of specification",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="author_1",
    )
    await repo.store(rec)
    assert rec.version == 1

    updated = await lifecycle_mgr.update(
        tenant_id="tenant_1",
        memory_id=rec.id,
        new_content="Final revised specification with security notes",
        metadata_updates={"reviewer": "alice", "reviewed": True},
    )

    assert updated.version == 2
    assert "Final revised specification" in updated.original_content
    assert updated.metadata["reviewer"] == "alice"


@pytest.mark.asyncio
async def test_lifecycle_operations_preserve_historical_knowledge(
    lifecycle_mgr: MemoryLifecycleManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Invariant test: Lifecycle transitions must NEVER silently destroy historical versions."""
    rec = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Original historical fact: Server location is us-east-1.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="admin",
        confidence=0.9,
    )
    await repo.store(rec)

    # Transition to superseded or archived
    archived = await lifecycle_mgr.archive(tenant_id="tenant_1", memory_id=rec.id)
    assert archived.status == LifecycleStatus.ARCHIVED

    # Verify original record is preserved in storage
    stored_rec = await repo.get_by_id("tenant_1", rec.id)
    assert stored_rec is not None
    assert stored_rec.original_content == "Original historical fact: Server location is us-east-1."
    assert stored_rec.status == LifecycleStatus.ARCHIVED

    # Restore back to active
    restored = await lifecycle_mgr.restore(tenant_id="tenant_1", memory_id=rec.id)
    assert restored.status == LifecycleStatus.ACTIVE


@pytest.mark.asyncio
async def test_run_lifecycle_cycle_maintenance(
    lifecycle_mgr: MemoryLifecycleManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test executing a full cognitive lifecycle maintenance cycle."""
    now = datetime.datetime.now(datetime.UTC)
    old_time = now - datetime.timedelta(days=120)

    # 1. Expired record
    expired_rec = MemoryRecord.create(
        tenant_id="tenant_cycle",
        content="Temporary 1-hour session token",
        memory_type=MemoryCategory.WORKING,
        author_id="auth_service",
        valid_from=old_time,
        valid_to=old_time + datetime.timedelta(hours=1),
    )

    # 2. Inactive low-salience record eligible for decay
    decay_candidate = MemoryRecord.create(
        tenant_id="tenant_cycle",
        content="Peripheral weather observation from last quarter",
        memory_type=MemoryCategory.EPISODIC,
        author_id="sensor",
        importance=0.1,
        asserted_at=old_time,
    )

    # 3. Two near-duplicate records eligible for consolidation
    c1 = MemoryRecord.create(
        tenant_id="tenant_cycle",
        content="User preferred Python 3.12 for backend services.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_1",
        confidence=0.9,
    )
    c2 = MemoryRecord.create(
        tenant_id="tenant_cycle",
        content="User preferred Python 3.12 for backend services and tooling.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_2",
        confidence=0.95,
    )

    await repo.store(expired_rec)
    await repo.store(decay_candidate)
    await repo.store(c1)
    await repo.store(c2)

    # Run cycle
    summary = await lifecycle_mgr.run_lifecycle_cycle(
        tenant_id="tenant_cycle",
        reference_time=now,
    )

    assert summary["tenant_id"] == "tenant_cycle"
    assert summary["expired_records"] == 0  # auto_archived_expired counted in auto_archived
    assert summary["auto_archived_expired"] == 1
    assert summary["decayed_records"] >= 1
    assert summary["consolidated_clusters"] >= 1
