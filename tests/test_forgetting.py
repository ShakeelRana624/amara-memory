"""Unit tests for AMARA forgetting subsystem, deletion, retention locks, and TTL expiration."""

from __future__ import annotations

import datetime

import pytest

from amara.enums import LifecycleStatus, MemoryCategory
from amara.exceptions import (
    RetentionLockError,
)
from amara.lifecycle.forgetting import ForgettingManager
from amara.lifecycle.types import LifecycleAction, RetentionPolicy
from amara.models.record import MemoryRecord
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def forgetting_mgr(repo: InMemoryMemoryRepository) -> ForgettingManager:
    return ForgettingManager(
        repository=repo,
        policy=RetentionPolicy(auto_archive_expired=True, respect_retention_locks=True),
    )


@pytest.mark.asyncio
async def test_soft_delete_transitions_to_tombstoned(
    forgetting_mgr: ForgettingManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test soft delete transitions memory to TOMBSTONED and records audit entry."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Temporary scratchpad notes",
        memory_type=MemoryCategory.WORKING,
        author_id="user_1",
    )
    await repo.store(record)

    success = await forgetting_mgr.delete_memory(
        tenant_id="tenant_acme",
        memory_id=record.id,
        hard=False,
    )
    assert success is True

    # Memory in repo is now tombstoned
    fetched = await repo.get_by_id("tenant_acme", record.id)
    assert fetched is not None
    assert fetched.status == LifecycleStatus.TOMBSTONED
    assert fetched.is_tombstoned is True

    # Audit log verification
    assert len(forgetting_mgr.audit_log) == 1
    audit = forgetting_mgr.audit_log[0]
    assert audit.action == LifecycleAction.DELETE
    assert audit.previous_status == LifecycleStatus.ACTIVE
    assert audit.new_status == LifecycleStatus.TOMBSTONED


@pytest.mark.asyncio
async def test_hard_delete_purges_record(
    forgetting_mgr: ForgettingManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test hard delete physically removes the record from storage."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Transient cache record",
        memory_type=MemoryCategory.WORKING,
        author_id="user_1",
    )
    await repo.store(record)

    success = await forgetting_mgr.delete_memory(
        tenant_id="tenant_acme",
        memory_id=record.id,
        hard=True,
    )
    assert success is True

    fetched = await repo.get_by_id("tenant_acme", record.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_retention_lock_prevents_deletion_unless_forced(
    forgetting_mgr: ForgettingManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that a record with retention_lock=True raises RetentionLockError upon delete."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Legal contract terms and retention policy",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="legal",
    )
    record.set_retention_lock(True)
    await repo.store(record)

    # Attempt delete without force=True
    with pytest.raises(RetentionLockError) as exc_info:
        await forgetting_mgr.delete_memory(
            tenant_id="tenant_acme",
            memory_id=record.id,
            hard=False,
            force=False,
        )
    assert "protected by a retention lock" in str(exc_info.value)

    # Force delete succeeds
    success = await forgetting_mgr.delete_memory(
        tenant_id="tenant_acme",
        memory_id=record.id,
        hard=False,
        force=True,
    )
    assert success is True


@pytest.mark.asyncio
async def test_archive_and_restore_operations(
    forgetting_mgr: ForgettingManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test transitioning memory to ARCHIVED and then restoring back to ACTIVE."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Archived project retrospective from Q1 2025",
        memory_type=MemoryCategory.EPISODIC,
        author_id="pm",
    )
    await repo.store(record)

    # Archive memory
    archived = await forgetting_mgr.archive_memory(tenant_id="tenant_acme", memory_id=record.id)
    assert archived.status == LifecycleStatus.ARCHIVED
    assert archived.is_archived is True

    fetched = await repo.get_by_id("tenant_acme", record.id)
    assert fetched is not None
    assert fetched.status == LifecycleStatus.ARCHIVED

    # Restore memory back to active
    restored = await forgetting_mgr.restore_memory(tenant_id="tenant_acme", memory_id=record.id)
    assert restored.status == LifecycleStatus.ACTIVE
    assert restored.is_active is True

    fetched_restored = await repo.get_by_id("tenant_acme", record.id)
    assert fetched_restored is not None
    assert fetched_restored.status == LifecycleStatus.ACTIVE


@pytest.mark.asyncio
async def test_ttl_expiration_scan(
    forgetting_mgr: ForgettingManager,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that expire_records scans and transitions expired records according to policy."""
    now = datetime.datetime.now(datetime.UTC)
    past_time = now - datetime.timedelta(days=5)

    # Valid record (unbounded future)
    valid_rec = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Valid active setting",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="user_1",
    )

    # Expired record without lock
    expired_rec = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Temporary 24h auth token",
        memory_type=MemoryCategory.WORKING,
        author_id="system",
        valid_from=now - datetime.timedelta(days=10),
        valid_to=past_time,
    )

    # Expired record WITH retention lock
    locked_expired_rec = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Expired audit log with permanent legal hold",
        memory_type=MemoryCategory.EPISODIC,
        author_id="legal",
        valid_from=now - datetime.timedelta(days=10),
        valid_to=past_time,
    )
    locked_expired_rec.set_retention_lock(True)

    await repo.store(valid_rec)
    await repo.store(expired_rec)
    await repo.store(locked_expired_rec)

    result = await forgetting_mgr.expire_records(
        tenant_id="tenant_acme",
        reference_time=now,
    )

    assert result.scanned_count >= 3
    assert result.archived_count == 1  # auto_archive_expired=True
    assert result.protected_by_lock_count == 1
    assert expired_rec.id in result.affected_memory_ids
    assert locked_expired_rec.id not in result.affected_memory_ids

    # Verify locked record remains active
    fetched_locked = await repo.get_by_id("tenant_acme", locked_expired_rec.id)
    assert fetched_locked is not None
    assert fetched_locked.status == LifecycleStatus.ACTIVE
