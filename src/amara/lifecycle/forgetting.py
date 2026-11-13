"""Adaptive forgetting, TTL expiration, retention locks, and safe memory removal."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from uuid import UUID

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus
from amara.exceptions import (
    MemoryNotFoundError,
    RetentionLockError,
    TenantIsolationError,
)
from amara.lifecycle.types import (
    ExpirationResult,
    LifecycleAction,
    LifecycleAuditRecord,
    RetentionPolicy,
)
from amara.models.record import MemoryRecord


class ForgettingManager:
    """Manages memory expiration, policy-driven archival, and safe deletion.

    Enforces:
    - User-controlled retention locks (records with retention_lock=True are protected).
    - Tenant isolation checks.
    - Verified cleanup of derived indexes and relationship edges.
    - Retention of historical knowledge without accidental silent purges.
    """

    def __init__(
        self,
        repository: MemoryRepository,
        policy: RetentionPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.policy = policy or RetentionPolicy()
        self._audit_log: list[LifecycleAuditRecord] = []

    @property
    def audit_log(self) -> Sequence[LifecycleAuditRecord]:
        """Return the in-memory audit log of executed forgetting operations."""
        return tuple(self._audit_log)

    async def delete_memory(
        self,
        tenant_id: str,
        memory_id: UUID,
        hard: bool = False,
        cascade: bool = False,
        force: bool = False,
        reason: str = "User deletion request",
    ) -> bool:
        """Delete a memory record using soft tombstoning or physical hard delete.

        Raises:
            MemoryNotFoundError: If the record does not exist in the specified tenant.
            RetentionLockError: If the record is protected by an active retention lock.
        """
        record = await self.repository.get_by_id(tenant_id, memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

        if record.tenant_id != tenant_id:
            raise TenantIsolationError(tenant_id, record.tenant_id)

        if record.is_retention_locked and not force:
            raise RetentionLockError(memory_id, action="delete")

        now = datetime.datetime.now(datetime.UTC)
        prev_status = record.status

        if hard:
            deleted_count = await self.repository.hard_delete(tenant_id, memory_id, cascade=cascade)
            success = deleted_count > 0
            new_status = LifecycleStatus.TOMBSTONED  # Denotes purged
        else:
            success = await self.repository.soft_delete(tenant_id, memory_id)
            new_status = LifecycleStatus.TOMBSTONED

        if success:
            self._audit_log.append(
                LifecycleAuditRecord(
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                    namespace=record.namespace,
                    action=LifecycleAction.DELETE,
                    previous_status=prev_status,
                    new_status=new_status,
                    reason=reason,
                    performed_at=now,
                    details={"hard": hard, "cascade": cascade, "force": force},
                )
            )

        return success

    async def archive_memory(
        self,
        tenant_id: str,
        memory_id: UUID,
        force: bool = False,
        reason: str = "Policy-driven archival",
    ) -> MemoryRecord:
        """Transition an active or decaying memory to ARCHIVED status.

        Raises:
            MemoryNotFoundError: If the record does not exist in the specified tenant.
            RetentionLockError: If the record is protected by a retention lock.
        """
        record = await self.repository.get_by_id(tenant_id, memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

        if record.is_retention_locked and not force:
            raise RetentionLockError(memory_id, action="archive")

        now = datetime.datetime.now(datetime.UTC)
        prev_status = record.status

        record.archive(archived_at=now)
        await self.repository.update_status(tenant_id, memory_id, LifecycleStatus.ARCHIVED)

        self._audit_log.append(
            LifecycleAuditRecord(
                memory_id=memory_id,
                tenant_id=tenant_id,
                namespace=record.namespace,
                action=LifecycleAction.ARCHIVE,
                previous_status=prev_status,
                new_status=LifecycleStatus.ARCHIVED,
                reason=reason,
                performed_at=now,
                details={"force": force},
            )
        )

        return record

    async def restore_memory(
        self,
        tenant_id: str,
        memory_id: UUID,
        reason: str = "Explicit memory restoration",
    ) -> MemoryRecord:
        """Restore an archived, superseded, or expired record back to ACTIVE status."""
        record = await self.repository.get_by_id(tenant_id, memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

        now = datetime.datetime.now(datetime.UTC)
        prev_status = record.status

        record.restore(restored_at=now)
        await self.repository.update_status(tenant_id, memory_id, LifecycleStatus.ACTIVE)

        self._audit_log.append(
            LifecycleAuditRecord(
                memory_id=memory_id,
                tenant_id=tenant_id,
                namespace=record.namespace,
                action=LifecycleAction.RESTORE,
                previous_status=prev_status,
                new_status=LifecycleStatus.ACTIVE,
                reason=reason,
                performed_at=now,
                details={},
            )
        )

        return record

    async def expire_records(
        self,
        tenant_id: str,
        namespace: str | None = None,
        reference_time: datetime.datetime | None = None,
    ) -> ExpirationResult:
        """Scan memories in tenant scope and transition temporally expired records.

        Records with valid_to < reference_time are expired or archived, unless
        protected by a retention lock.
        """
        ref = reference_time or datetime.datetime.now(datetime.UTC)

        # Retrieve active and decaying memories
        query_spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=tenant_id,
                namespace=namespace,
                statuses=(LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING),
            ),
            top_k=1000,
        )
        candidates = await self.repository.query(query_spec)

        scanned = len(candidates)
        expired_count = 0
        archived_count = 0
        locked_count = 0
        affected_ids: list[UUID] = []

        for record in candidates:
            # Check temporal validity
            if record.temporal.valid_to is not None and record.temporal.valid_to < ref:
                if record.is_retention_locked and self.policy.respect_retention_locks:
                    locked_count += 1
                    continue

                prev_status = record.status
                if self.policy.auto_archive_expired:
                    record.archive(archived_at=ref)
                    target_status = LifecycleStatus.ARCHIVED
                    archived_count += 1
                    action = LifecycleAction.ARCHIVE
                else:
                    record.expire(expired_at=ref)
                    target_status = LifecycleStatus.EXPIRED
                    expired_count += 1
                    action = LifecycleAction.EXPIRE

                await self.repository.update_status(tenant_id, record.id, target_status)
                affected_ids.append(record.id)

                self._audit_log.append(
                    LifecycleAuditRecord(
                        memory_id=record.id,
                        tenant_id=tenant_id,
                        namespace=record.namespace,
                        action=action,
                        previous_status=prev_status,
                        new_status=target_status,
                        reason=(
                            f"Temporal validity window expired at "
                            f"{record.temporal.valid_to.isoformat()}"
                        ),
                        performed_at=ref,
                        details={"valid_to": record.temporal.valid_to.isoformat()},
                    )
                )

        return ExpirationResult(
            tenant_id=tenant_id,
            namespace=namespace,
            scanned_count=scanned,
            expired_count=expired_count,
            archived_count=archived_count,
            protected_by_lock_count=locked_count,
            affected_memory_ids=tuple(affected_ids),
        )
