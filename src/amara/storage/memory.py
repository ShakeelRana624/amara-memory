"""Thread-safe, high-performance in-memory reference implementation of MemoryRepository.

Designed for fast automated testing, local development, edge environments, and ephemeral sessions.
"""

from __future__ import annotations

import asyncio
import datetime
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from amara.contracts.query import QuerySpec
from amara.enums import LifecycleStatus, RelationType
from amara.exceptions import (
    ConcurrencyError,
    DuplicateMemoryError,
    MemoryNotFoundError,
    RepositoryError,
    StorageCapacityExceededError,
)
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.storage.vector_math import cosine_similarity


class InMemoryMemoryRepository:
    """In-memory reference storage backend implementing MemoryRepository protocol.

    Provides complete multi-tenant partitioning, bitemporal querying, cosine vector ranking,
    and cascading hard/soft deletions with asyncio locking for concurrent safety.
    """

    def __init__(self, max_capacity: int = 100_000) -> None:
        self.max_capacity = max_capacity
        self._lock = asyncio.Lock()
        # Tenant partitioned storage: tenant_id -> {memory_id: MemoryRecord}
        self._records: dict[str, dict[UUID, MemoryRecord]] = defaultdict(dict)
        # Tenant partitioned associations: tenant_id -> {relationship_id: MemoryRelationship}
        self._associations: dict[str, dict[UUID, MemoryRelationship]] = defaultdict(dict)
        self._is_initialized: bool = False

    async def initialize(self) -> None:
        """Mark the repository as initialized and ready."""
        async with self._lock:
            self._is_initialized = True

    async def close(self) -> None:
        """Clear memory structures and mark repository as closed."""
        async with self._lock:
            self._records.clear()
            self._associations.clear()
            self._is_initialized = False

    async def create_memory(self, record: MemoryRecord) -> MemoryRecord:
        """Persist a new memory record, ensuring tenant isolation and uniqueness."""
        await self.store(record)
        return record

    async def store(self, record: MemoryRecord) -> None:
        """Store a single memory record transactionally with capacity and duplicate checks."""
        async with self._lock:
            tenant_store = self._records[record.tenant_id]

            if len(tenant_store) >= self.max_capacity and record.id not in tenant_store:
                raise StorageCapacityExceededError(len(tenant_store), self.max_capacity)

            if record.id in tenant_store:
                raise DuplicateMemoryError(record.id, tenant_id=record.tenant_id)

            tenant_store[record.id] = record

    async def store_batch(self, records: Sequence[MemoryRecord]) -> None:
        """Store a batch of memory records atomically, rolling back on failure."""
        async with self._lock:
            if not records:
                return

            tenant_ids = {r.tenant_id for r in records}
            # Verify capacity across tenants
            for tid in tenant_ids:
                tenant_recs = [r for r in records if r.tenant_id == tid]
                if len(self._records[tid]) + len(tenant_recs) > self.max_capacity:
                    raise StorageCapacityExceededError(len(self._records[tid]), self.max_capacity)

            # Check for duplicate IDs either against store or within batch
            seen_ids: set[UUID] = set()
            for r in records:
                if r.id in seen_ids or r.id in self._records[r.tenant_id]:
                    raise DuplicateMemoryError(r.id, tenant_id=r.tenant_id)
                seen_ids.add(r.id)

            # Commit batch
            for r in records:
                self._records[r.tenant_id][r.id] = r

    async def get_memory(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Fetch a specific record by ID within tenant scope."""
        return await self.get_by_id(tenant_id, memory_id)

    async def get_by_id(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Fetch a specific record by ID within tenant scope."""
        async with self._lock:
            return self._records.get(tenant_id, {}).get(memory_id)

    async def query(self, spec: QuerySpec) -> Sequence[MemoryRecord]:
        """Execute structured search over memory records with hybrid filters."""
        async with self._lock:
            q_filter = spec.filter
            tenant_store = self._records.get(q_filter.tenant_id, {})
            candidates: list[MemoryRecord] = []

            for record in tenant_store.values():
                # Namespace check
                if q_filter.namespace is not None and record.namespace != q_filter.namespace:
                    continue

                # Status check
                if not spec.include_tombstoned and record.is_tombstoned:
                    continue
                if q_filter.statuses and record.status not in q_filter.statuses:
                    continue

                # Memory type check
                if q_filter.memory_types and record.memory_type not in q_filter.memory_types:
                    continue

                # Confidence and Importance bounds
                if record.confidence < spec.min_confidence:
                    continue
                if record.importance < spec.min_importance:
                    continue

                # Temporal validity check
                ref_time = q_filter.valid_at or q_filter.reference_time
                if ref_time is not None and not record.is_valid_at(ref_time):
                    continue

                # Created timestamps check
                if (
                    q_filter.created_after is not None
                    and record.created_at < q_filter.created_after
                ):
                    continue
                if (
                    q_filter.created_before is not None
                    and record.created_at > q_filter.created_before
                ):
                    continue

                # Attribution filters
                if q_filter.author_id is not None and record.source.author_id != q_filter.author_id:
                    continue
                if (
                    q_filter.session_id is not None
                    and record.source.session_id != q_filter.session_id
                ):
                    continue
                if q_filter.source_id is not None and record.source.source_id != q_filter.source_id:
                    continue

                # Metadata key-value matching
                if q_filter.metadata_filter:
                    match = True
                    for k, v in q_filter.metadata_filter.items():
                        if record.metadata.get(k) != v:
                            match = False
                            break
                    if not match:
                        continue

                candidates.append(record)

            # Relationship expansion if requested
            if spec.expand_relationships and spec.max_relationship_hops >= 1:
                adjacent_ids: set[UUID] = set()
                tenant_assocs = self._associations.get(q_filter.tenant_id, {})
                candidate_ids = {c.id for c in candidates}

                for assoc in tenant_assocs.values():
                    if assoc.source_id in candidate_ids and assoc.target_id not in candidate_ids:
                        adjacent_ids.add(assoc.target_id)
                    elif (
                        assoc.bidirectional
                        and assoc.target_id in candidate_ids
                        and assoc.source_id not in candidate_ids
                    ):
                        adjacent_ids.add(assoc.source_id)

                for adj_id in adjacent_ids:
                    adj_rec = tenant_store.get(adj_id)
                    if adj_rec and (spec.include_tombstoned or not adj_rec.is_tombstoned):
                        candidates.append(adj_rec)

            # Vector similarity ranking
            if spec.query_vector is not None:
                scored_candidates: list[tuple[float, MemoryRecord]] = []
                for rec in candidates:
                    if rec.embedding is not None and len(rec.embedding) == len(spec.query_vector):
                        sim = cosine_similarity(spec.query_vector, rec.embedding)
                    else:
                        sim = -1.0
                    scored_candidates.append((sim, rec))

                scored_candidates.sort(key=lambda item: item[0], reverse=True)
                candidates = [rec for _, rec in scored_candidates]

            # Lexical fallback filtering if query_text is given without vector
            elif spec.query_text:
                q_lower = spec.query_text.lower().strip()
                candidates = [
                    rec for rec in candidates if q_lower in rec.normalized_content.lower()
                ]

            return candidates[: spec.top_k]

    async def count(self, tenant_id: str, namespace: str | None = None) -> int:
        """Count active, non-tombstoned records in tenant scope."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id, {})
            if namespace is None:
                return sum(1 for r in tenant_store.values() if not r.is_tombstoned)
            return sum(
                1 for r in tenant_store.values() if r.namespace == namespace and not r.is_tombstoned
            )

    async def update_memory(
        self,
        tenant_id: str,
        memory_id: UUID,
        expected_version: int,
        content: str | None = None,
        status: LifecycleStatus | None = None,
        metadata: Mapping[str, Any] | None = None,
        _changed_by: str = "system",
        _change_reason: str | None = None,
    ) -> MemoryRecord:
        """Controlled update of a memory record with optimistic concurrency validation."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id)
            if not tenant_store or memory_id not in tenant_store:
                raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

            rec = tenant_store[memory_id]
            if rec.version != expected_version:
                raise ConcurrencyError(
                    f"Optimistic concurrency failure: record version {rec.version} does not match "
                    f"expected {expected_version}."
                )

            now = datetime.datetime.now(datetime.UTC)
            if content is not None:
                rec.update_content(content, updated_at=now)
            if status is not None:
                rec.update_status(status, updated_at=now)
            if metadata is not None:
                merged = dict(rec.metadata)
                merged.update(metadata)
                rec.metadata = merged
                rec.updated_at = now

            return rec

    async def update_status(self, tenant_id: str, memory_id: UUID, status: LifecycleStatus) -> None:
        """Update lifecycle status of a memory record."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id)
            if not tenant_store or memory_id not in tenant_store:
                raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)
            tenant_store[memory_id].update_status(status)

    async def update_metrics(
        self,
        tenant_id: str,
        memory_id: UUID,
        utility_delta: float,
        accessed_at: datetime.datetime,
    ) -> None:
        """Record access event and reinforce utility score."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id)
            if not tenant_store or memory_id not in tenant_store:
                raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)
            tenant_store[memory_id].record_access(
                utility_delta=utility_delta, accessed_at=accessed_at
            )

    async def soft_delete(self, tenant_id: str, memory_id: UUID) -> bool:
        """Transition record to TOMBSTONED lifecycle status."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id)
            if not tenant_store or memory_id not in tenant_store:
                raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)
            tenant_store[memory_id].soft_delete()
            return True

    async def hard_delete(self, tenant_id: str, memory_id: UUID, cascade: bool = False) -> int:
        """Permanently delete a record, optionally cascading along derivation lineages."""
        async with self._lock:
            tenant_store = self._records.get(tenant_id)
            if not tenant_store or memory_id not in tenant_store:
                raise MemoryNotFoundError(memory_id, tenant_id=tenant_id)

            deleted_ids: set[UUID] = {memory_id}

            if cascade:
                # Find all derived records where memory_id is in parent_ids
                to_evaluate = [memory_id]
                while to_evaluate:
                    curr_parent = to_evaluate.pop()
                    for rec_id, rec in list(tenant_store.items()):
                        if rec_id in deleted_ids:
                            continue
                        if curr_parent in rec.parent_ids:
                            # Check if child has other surviving parents
                            surviving_parents = [
                                pid for pid in rec.parent_ids if pid not in deleted_ids
                            ]
                            if not surviving_parents:
                                deleted_ids.add(rec_id)
                                to_evaluate.append(rec_id)
                            else:
                                # Child has other parents: prune deleted parent from list
                                rec.parent_ids = tuple(surviving_parents)

            # Physically remove records
            for d_id in deleted_ids:
                tenant_store.pop(d_id, None)

            # Purge associated relationship edges involving any deleted record
            tenant_assocs = self._associations.get(tenant_id, {})
            edge_ids_to_remove = [
                eid
                for eid, edge in tenant_assocs.items()
                if edge.source_id in deleted_ids or edge.target_id in deleted_ids
            ]
            for eid in edge_ids_to_remove:
                tenant_assocs.pop(eid, None)

            return len(deleted_ids)

    async def create_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        """Create a relational association between two records."""
        await self.add_relationship(relationship)
        return relationship

    async def add_relationship(self, relationship: MemoryRelationship) -> None:
        """Store a relationship edge, verifying both connected nodes exist in tenant store."""
        async with self._lock:
            tenant_store = self._records.get(relationship.tenant_id, {})
            if relationship.source_id not in tenant_store:
                raise RepositoryError(
                    f"Relationship source memory '{relationship.source_id}' does not exist "
                    f"in tenant '{relationship.tenant_id}'."
                )
            if relationship.target_id not in tenant_store:
                raise RepositoryError(
                    f"Relationship target memory '{relationship.target_id}' does not exist "
                    f"in tenant '{relationship.tenant_id}'."
                )

            self._associations[relationship.tenant_id][relationship.relationship_id] = relationship

    async def get_relationships(
        self,
        tenant_id: str,
        memory_id: UUID,
        relation_type: RelationType | None = None,
    ) -> Sequence[MemoryRelationship]:
        """Fetch association edges connected to memory_id within tenant scope."""
        async with self._lock:
            tenant_assocs = self._associations.get(tenant_id, {})
            results: list[MemoryRelationship] = []

            for edge in tenant_assocs.values():
                matches_node = edge.source_id == memory_id or (
                    edge.bidirectional and edge.target_id == memory_id
                )
                if matches_node and (relation_type is None or edge.relation_type == relation_type):
                    results.append(edge)

            return results
