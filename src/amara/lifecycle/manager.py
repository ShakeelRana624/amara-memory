"""Unified lifecycle manager orchestrating retention, decay, consolidation, and forgetting."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus
from amara.exceptions import (
    MemoryNotFoundError,
)
from amara.intelligence.contradiction import ContradictionDetector
from amara.lifecycle.consolidation import MemoryConsolidator
from amara.lifecycle.forgetting import ForgettingManager
from amara.lifecycle.policies import MemoryPolicyManager
from amara.lifecycle.types import (
    ConsolidationPolicy,
    ConsolidationResult,
    ExpirationResult,
    LifecycleAction,
    LifecycleAuditRecord,
    RetentionPolicy,
)
from amara.models.record import MemoryRecord


class MemoryLifecycleManager:
    """The central orchestrator for AMARA's cognitive memory lifecycle.

    Coordinates:
    - Retain: access reinforcement and utility scoring.
    - Update: controlled content and version evolution.
    - Consolidate: duplicate clustering and episodic-to-semantic synthesis.
    - Archive: cold storage transitions.
    - Restore: reactivating archived/superseded memories.
    - Expire: TTL expiration.
    - Delete: safe soft-tombstoning and cascading hard deletes.
    """

    def __init__(
        self,
        repository: MemoryRepository,
        retention_policy: RetentionPolicy | None = None,
        consolidation_policy: ConsolidationPolicy | None = None,
        contradiction_detector: ContradictionDetector | None = None,
    ) -> None:
        self.repository = repository
        self.retention_policy = retention_policy or RetentionPolicy()
        self.consolidation_policy = consolidation_policy or ConsolidationPolicy()

        self.policy_manager = MemoryPolicyManager(policy=self.retention_policy)
        self.forgetting_manager = ForgettingManager(
            repository=self.repository,
            policy=self.retention_policy,
        )
        self.consolidator = MemoryConsolidator(
            repository=self.repository,
            contradiction_detector=contradiction_detector or ContradictionDetector(),
            policy=self.consolidation_policy,
        )

    @property
    def audit_log(self) -> Sequence[LifecycleAuditRecord]:
        """Return the complete audit trail of lifecycle actions."""
        return self.forgetting_manager.audit_log

    # -----------------------------------------------------------------------
    # Core Lifecycle Operations
    # -----------------------------------------------------------------------

    async def retain(
        self,
        tenant_id: str,
        memory_id: UUID,
        utility_delta: float = 1.0,
        accessed_at: datetime.datetime | None = None,
    ) -> MemoryRecord:
        """Reinforce and retain a memory record upon retrieval access."""
        record = await self.repository.get_by_id(tenant_id, memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

        now = accessed_at or datetime.datetime.now(datetime.UTC)

        # If decaying, retrieval reinforcement transitions it back to active
        if record.status == LifecycleStatus.DECAYING:
            await self.repository.update_status(tenant_id, memory_id, LifecycleStatus.ACTIVE)

        await self.repository.update_metrics(
            tenant_id=tenant_id,
            memory_id=memory_id,
            utility_delta=utility_delta,
            accessed_at=now,
        )
        updated = await self.repository.get_by_id(tenant_id, memory_id)
        return updated or record

    async def update(
        self,
        tenant_id: str,
        memory_id: UUID,
        new_content: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
        _updated_at: datetime.datetime | None = None,
    ) -> MemoryRecord:
        """Perform a controlled update of a memory record's content or metadata."""
        record = await self.repository.get_by_id(tenant_id, memory_id)
        if record is None:
            raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

        return await self.repository.update_memory(
            tenant_id=tenant_id,
            memory_id=memory_id,
            expected_version=record.version,
            content=new_content,
            metadata=metadata_updates,
        )

    async def consolidate(
        self,
        tenant_id: str,
        namespace: str = "default",
    ) -> list[ConsolidationResult]:
        """Discover clusters of related memories in namespace and synthesize semantic knowledge."""
        query_spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=tenant_id,
                namespace=namespace,
                statuses=(LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING),
            ),
            top_k=500,
        )
        records = await self.repository.query(query_spec)
        record_map = {r.id: r for r in records}

        candidates = self.consolidator.find_consolidation_candidates(records)
        results: list[ConsolidationResult] = []

        for cand in candidates:
            res = await self.consolidator.consolidate_candidate(cand, record_map)
            results.append(res)

        return results

    async def archive(
        self,
        tenant_id: str,
        memory_id: UUID,
        force: bool = False,
        reason: str = "Explicit archive request",
    ) -> MemoryRecord:
        """Transition a memory to ARCHIVED status."""
        return await self.forgetting_manager.archive_memory(
            tenant_id=tenant_id,
            memory_id=memory_id,
            force=force,
            reason=reason,
        )

    async def restore(
        self,
        tenant_id: str,
        memory_id: UUID,
        reason: str = "Explicit restore request",
    ) -> MemoryRecord:
        """Restore an archived, superseded, or expired memory back to ACTIVE status."""
        return await self.forgetting_manager.restore_memory(
            tenant_id=tenant_id,
            memory_id=memory_id,
            reason=reason,
        )

    async def expire(
        self,
        tenant_id: str,
        namespace: str | None = None,
        reference_time: datetime.datetime | None = None,
    ) -> ExpirationResult:
        """Execute a TTL / temporal validity expiration scan."""
        return await self.forgetting_manager.expire_records(
            tenant_id=tenant_id,
            namespace=namespace,
            reference_time=reference_time,
        )

    async def delete(
        self,
        tenant_id: str,
        memory_id: UUID,
        hard: bool = False,
        cascade: bool = False,
        force: bool = False,
        reason: str = "User deletion request",
    ) -> bool:
        """Delete a memory record using soft tombstone or physical purge."""
        return await self.forgetting_manager.delete_memory(
            tenant_id=tenant_id,
            memory_id=memory_id,
            hard=hard,
            cascade=cascade,
            force=force,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Comprehensive Lifecycle Automation Cycle
    # -----------------------------------------------------------------------

    async def run_lifecycle_cycle(
        self,
        tenant_id: str,
        namespace: str | None = None,
        reference_time: datetime.datetime | None = None,
    ) -> dict[str, Any]:
        """Execute a complete cognitive maintenance cycle for a tenant.

        1. TTL Expiration: scan and expire/archive invalid temporal windows.
        2. Policy Evaluation: transition active -> decaying, decaying -> archived.
        3. Consolidation: discover duplicate/related clusters and synthesize semantic concepts.
        """
        ref = reference_time or datetime.datetime.now(datetime.UTC)

        # 1. TTL Expiration
        expiration_result = await self.expire(
            tenant_id=tenant_id,
            namespace=namespace,
            reference_time=ref,
        )

        # 2. Policy Evaluation and Decay/Archival Transitions
        query_spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=tenant_id,
                namespace=namespace,
                statuses=(LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING),
            ),
            top_k=1000,
        )
        pool = await self.repository.query(query_spec)

        decayed_count = 0
        archived_count = 0

        for record in pool:
            eval_res = self.policy_manager.evaluate_record(record, reference_time=ref)

            if eval_res.recommended_action == LifecycleAction.DECAY:
                record.update_status(LifecycleStatus.DECAYING, updated_at=ref)
                await self.repository.update_status(tenant_id, record.id, LifecycleStatus.DECAYING)
                decayed_count += 1

            elif eval_res.recommended_action == LifecycleAction.ARCHIVE:
                record.archive(archived_at=ref)
                await self.repository.update_status(tenant_id, record.id, LifecycleStatus.ARCHIVED)
                archived_count += 1

        # 3. Consolidation
        effective_ns = namespace or "default"
        consolidation_results = await self.consolidate(
            tenant_id=tenant_id,
            namespace=effective_ns,
        )

        return {
            "tenant_id": tenant_id,
            "namespace": namespace,
            "evaluated_at": ref.isoformat(),
            "scanned_records": len(pool),
            "expired_records": expiration_result.expired_count,
            "auto_archived_expired": expiration_result.archived_count,
            "decayed_records": decayed_count,
            "archived_records": archived_count,
            "consolidated_clusters": len(consolidation_results),
            "new_semantic_memories_created": len(consolidation_results),
        }
