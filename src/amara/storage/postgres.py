"""PostgreSQL 16+ production storage implementation with pgvector and optimistic concurrency."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError

from amara.contracts.query import QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    MemoryEventType,
    RelationType,
)
from amara.exceptions import (
    DuplicateMemoryError,
    InvalidMemoryStateError,
    MemoryNotFoundError,
    RepositoryError,
)
from amara.models.event import MemoryEvent
from amara.models.record import LEGAL_TRANSITIONS, MemoryRecord, normalize_text
from amara.models.relationship import MemoryRelationship
from amara.storage.database import DatabaseManager
from amara.storage.mappers import (
    event_to_orm,
    memory_record_to_orm,
    orm_to_event,
    orm_to_memory_record,
    orm_to_relationship,
    relationship_to_orm,
)
from amara.storage.schema import (
    Base,
    MemoryEventORM,
    MemoryRecordORM,
    MemoryRelationshipORM,
    MemoryVersionHistoryORM,
)


class PostgresMemoryRepository(MemoryRepository):
    """Production PostgreSQL 16+ storage repository with pgvector and concurrency controls."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    async def initialize(self) -> None:
        """Initialize database connection pool and ensure database tables exist."""
        await self.db.initialize()
        async with self.db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Dispose of database connection pool."""
        await self.db.close()

    # -----------------------------------------------------------------------
    # Core Memory Operations
    # -----------------------------------------------------------------------

    async def create_memory(self, record: MemoryRecord) -> MemoryRecord:
        """Persist a new memory record, ensuring tenant isolation and uniqueness."""
        await self.store(record)
        return record

    async def store(self, record: MemoryRecord) -> None:
        """Persist a single memory record transactionally."""
        orm_entity = memory_record_to_orm(record)
        event = MemoryEvent(
            tenant_id=record.tenant_id,
            namespace=record.namespace,
            memory_id=record.id,
            event_type=MemoryEventType.CREATED,
            payload={"version": record.version, "memory_type": record.memory_type.value},
        )
        event_orm = event_to_orm(event)

        async with self.db.session(tenant_id=record.tenant_id) as session:
            try:
                session.add(orm_entity)
                session.add(event_orm)
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                raise DuplicateMemoryError(record.id, tenant_id=record.tenant_id) from exc

    async def store_batch(self, records: Sequence[MemoryRecord]) -> None:
        """Persist a sequence of memory records atomically."""
        if not records:
            return

        tenant_ids = {r.tenant_id for r in records}
        # If multi-tenant batch, process per tenant transactionally
        for tid in tenant_ids:
            tenant_records = [r for r in records if r.tenant_id == tid]
            async with self.db.session(tenant_id=tid) as session:
                try:
                    for r in tenant_records:
                        session.add(memory_record_to_orm(r))
                        session.add(
                            event_to_orm(
                                MemoryEvent(
                                    tenant_id=r.tenant_id,
                                    namespace=r.namespace,
                                    memory_id=r.id,
                                    event_type=MemoryEventType.CREATED,
                                    payload={"version": r.version},
                                )
                            )
                        )
                    await session.flush()
                except IntegrityError as exc:
                    await session.rollback()
                    raise RepositoryError(
                        f"Failed to store batch for tenant '{tid}': {exc}"
                    ) from exc

    async def get_memory(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Fetch a memory record by ID within tenant scope."""
        return await self.get_by_id(tenant_id, memory_id)

    async def get_by_id(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Fetch a specific memory record by primary key."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = select(MemoryRecordORM).where(
                MemoryRecordORM.id == memory_id,
                MemoryRecordORM.tenant_id == clean_tenant,
            )
            result = await session.execute(stmt)
            orm_record = result.scalar_one_or_none()
            if orm_record is None:
                return None
            return orm_to_memory_record(orm_record)

    async def update_memory(
        self,
        tenant_id: str,
        memory_id: UUID,
        expected_version: int,
        content: str | None = None,
        status: LifecycleStatus | None = None,
        metadata: Mapping[str, Any] | None = None,
        changed_by: str = "system",
        change_reason: str | None = None,
    ) -> MemoryRecord:
        """Controlled update of a memory record with optimistic concurrency validation."""
        clean_tenant = tenant_id.strip()
        now = datetime.datetime.now(datetime.UTC)

        async with self.db.session(tenant_id=clean_tenant) as session:
            # 1. Fetch current record
            stmt = select(MemoryRecordORM).where(
                MemoryRecordORM.id == memory_id,
                MemoryRecordORM.tenant_id == clean_tenant,
            )
            res = await session.execute(stmt)
            orm_record = res.scalar_one_or_none()
            if orm_record is None:
                raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)

            # 2. Check optimistic concurrency
            if orm_record.version != expected_version:
                msg = (
                    f"Optimistic lock conflict: record '{memory_id}' is at version "
                    f"{orm_record.version}, expected {expected_version}"
                )
                raise InvalidMemoryStateError(
                    f"version_{orm_record.version}",
                    f"version_{expected_version}",
                    reason=msg,
                )

            # 3. Snapshot current state into version history
            history_entry = MemoryVersionHistoryORM(
                history_id=uuid4(),
                memory_id=orm_record.id,
                tenant_id=clean_tenant,
                version=orm_record.version,
                original_content=orm_record.original_content,
                normalized_content=orm_record.normalized_content,
                status=orm_record.status,
                metadata_payload=dict(orm_record.metadata_payload or {}),
                changed_at=now,
                changed_by=changed_by,
                change_reason=change_reason,
            )
            session.add(history_entry)

            # 4. Apply updates
            new_version = orm_record.version + 1
            update_values: dict[str, Any] = {
                "version": new_version,
                "updated_at": now,
            }

            if content is not None:
                clean_content = content.strip()
                if not clean_content:
                    raise RepositoryError("Cannot update memory to empty content.")
                update_values["original_content"] = clean_content
                update_values["normalized_content"] = normalize_text(clean_content)

            if status is not None:
                current_status = LifecycleStatus(orm_record.status)
                if status not in LEGAL_TRANSITIONS.get(current_status, set()):
                    raise InvalidMemoryStateError(current_status.value, status.value)
                update_values["status"] = status.value

            if metadata is not None:
                merged_metadata = dict(orm_record.metadata_payload or {})
                merged_metadata.update(metadata)
                update_values["metadata_payload"] = merged_metadata

            # 5. Execute atomic UPDATE with optimistic condition
            update_stmt = (
                update(MemoryRecordORM)
                .where(
                    MemoryRecordORM.id == memory_id,
                    MemoryRecordORM.tenant_id == clean_tenant,
                    MemoryRecordORM.version == expected_version,
                )
                .values(**update_values)
            )
            update_result = cast(CursorResult[Any], await session.execute(update_stmt))
            if update_result.rowcount == 0:
                raise InvalidMemoryStateError(
                    f"version_{orm_record.version}",
                    f"version_{expected_version}",
                    reason="Optimistic concurrency race condition detected.",
                )

            # 6. Record domain event
            event = MemoryEvent(
                tenant_id=clean_tenant,
                namespace=orm_record.namespace,
                memory_id=memory_id,
                event_type=MemoryEventType.UPDATED,
                payload={"previous_version": expected_version, "new_version": new_version},
            )
            session.add(event_to_orm(event))

        # Re-fetch updated record
        updated_rec = await self.get_by_id(clean_tenant, memory_id)
        if updated_rec is None:
            raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)
        return updated_rec

    async def delete_memory(
        self, tenant_id: str, memory_id: UUID, hard: bool = False, cascade: bool = False
    ) -> int:
        """Delete memory record via soft tombstone or hard cascade purge."""
        if not hard:
            success = await self.soft_delete(tenant_id, memory_id)
            return 1 if success else 0
        return await self.hard_delete(tenant_id, memory_id, cascade=cascade)

    async def soft_delete(self, tenant_id: str, memory_id: UUID) -> bool:
        """Mark record as TOMBSTONED."""
        clean_tenant = tenant_id.strip()
        now = datetime.datetime.now(datetime.UTC)
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = (
                update(MemoryRecordORM)
                .where(
                    MemoryRecordORM.id == memory_id,
                    MemoryRecordORM.tenant_id == clean_tenant,
                )
                .values(
                    status=LifecycleStatus.TOMBSTONED.value,
                    deleted_at=now,
                    updated_at=now,
                )
            )
            res = cast(CursorResult[Any], await session.execute(stmt))
            if res.rowcount == 0:
                raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)

            event = MemoryEvent(
                tenant_id=clean_tenant,
                namespace="default",
                memory_id=memory_id,
                event_type=MemoryEventType.TOMBSTONED,
            )
            session.add(event_to_orm(event))
            return True

    async def hard_delete(self, tenant_id: str, memory_id: UUID, cascade: bool = False) -> int:
        """Irreversibly delete a record and optionally cascade to dependent derived memories."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            # Check target exists
            check_stmt = select(MemoryRecordORM.id).where(
                MemoryRecordORM.id == memory_id,
                MemoryRecordORM.tenant_id == clean_tenant,
            )
            exists = (await session.execute(check_stmt)).scalar_one_or_none()
            if exists is None:
                raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)

            deleted_count = 0

            if cascade:
                # Find all records where memory_id is in parent_ids
                descendants_stmt = select(MemoryRecordORM).where(
                    MemoryRecordORM.tenant_id == clean_tenant,
                    MemoryRecordORM.parent_ids.contains([memory_id]),
                )
                descendants = (await session.execute(descendants_stmt)).scalars().all()

                for child in descendants:
                    surviving_parents = [p for p in child.parent_ids if p != memory_id]
                    if not surviving_parents:
                        # Orphaned child: delete child recursively
                        del_child_stmt = delete(MemoryRecordORM).where(
                            MemoryRecordORM.id == child.id,
                            MemoryRecordORM.tenant_id == clean_tenant,
                        )
                        await session.execute(del_child_stmt)
                        deleted_count += 1
                    else:
                        # Has other parents: prune parent list
                        child.parent_ids = surviving_parents

            # Delete the target record
            del_stmt = delete(MemoryRecordORM).where(
                MemoryRecordORM.id == memory_id,
                MemoryRecordORM.tenant_id == clean_tenant,
            )
            del_res = cast(CursorResult[Any], await session.execute(del_stmt))
            deleted_count += int(del_res.rowcount or 0)

            event = MemoryEvent(
                tenant_id=clean_tenant,
                namespace="default",
                memory_id=memory_id,
                event_type=MemoryEventType.PURGED,
                payload={"cascade": cascade, "total_purged": deleted_count},
            )
            session.add(event_to_orm(event))
            return deleted_count

    async def list_memories(
        self,
        tenant_id: str,
        namespace: str | None = None,
        memory_types: Sequence[MemoryCategory] | None = None,
        statuses: Sequence[LifecycleStatus] | None = None,
        valid_at: datetime.datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[MemoryRecord]:
        """List memory records with pagination and filters."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = select(MemoryRecordORM).where(MemoryRecordORM.tenant_id == clean_tenant)

            if namespace is not None:
                stmt = stmt.where(MemoryRecordORM.namespace == namespace)

            if memory_types:
                stmt = stmt.where(MemoryRecordORM.memory_type.in_([m.value for m in memory_types]))

            if statuses:
                stmt = stmt.where(MemoryRecordORM.status.in_([s.value for s in statuses]))
            else:
                stmt = stmt.where(MemoryRecordORM.status != LifecycleStatus.TOMBSTONED.value)

            if valid_at is not None:
                stmt = stmt.where(
                    MemoryRecordORM.valid_from <= valid_at,
                    (MemoryRecordORM.valid_to.is_(None)) | (MemoryRecordORM.valid_to > valid_at),
                )

            stmt = stmt.order_by(MemoryRecordORM.created_at.desc()).limit(limit).offset(offset)
            results = (await session.execute(stmt)).scalars().all()
            return [orm_to_memory_record(r) for r in results]

    async def count(self, tenant_id: str, namespace: str | None = None) -> int:
        """Count active records in tenant scope."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = select(func.count(MemoryRecordORM.id)).where(
                MemoryRecordORM.tenant_id == clean_tenant,
                MemoryRecordORM.status != LifecycleStatus.TOMBSTONED.value,
            )
            if namespace is not None:
                stmt = stmt.where(MemoryRecordORM.namespace == namespace)
            count_val = (await session.execute(stmt)).scalar_one()
            return int(count_val)

    async def update_status(self, tenant_id: str, memory_id: UUID, status: LifecycleStatus) -> None:
        """Update lifecycle status directly."""
        clean_tenant = tenant_id.strip()
        now = datetime.datetime.now(datetime.UTC)
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = (
                update(MemoryRecordORM)
                .where(
                    MemoryRecordORM.id == memory_id,
                    MemoryRecordORM.tenant_id == clean_tenant,
                )
                .values(status=status.value, updated_at=now)
            )
            res = cast(CursorResult[Any], await session.execute(stmt))
            if res.rowcount == 0:
                raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)

    async def update_metrics(
        self,
        tenant_id: str,
        memory_id: UUID,
        utility_delta: float,
        accessed_at: datetime.datetime,
    ) -> None:
        """Increment access count and apply utility score reinforcement."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = (
                update(MemoryRecordORM)
                .where(
                    MemoryRecordORM.id == memory_id,
                    MemoryRecordORM.tenant_id == clean_tenant,
                )
                .values(
                    access_count=MemoryRecordORM.access_count + 1,
                    utility_score=MemoryRecordORM.utility_score + utility_delta,
                    last_accessed_at=accessed_at,
                    updated_at=accessed_at,
                )
            )
            res = cast(CursorResult[Any], await session.execute(stmt))
            if res.rowcount == 0:
                raise MemoryNotFoundError(memory_id, tenant_id=clean_tenant)

    # -----------------------------------------------------------------------
    # Relationship Operations
    # -----------------------------------------------------------------------

    async def create_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        """Create a relational association between two records."""
        await self.add_relationship(relationship)
        return relationship

    async def add_relationship(self, relationship: MemoryRelationship) -> None:
        """Store an association edge."""
        orm_edge = relationship_to_orm(relationship)
        async with self.db.session(tenant_id=relationship.tenant_id) as session:
            try:
                session.add(orm_edge)
                await session.flush()
            except IntegrityError as exc:
                await session.rollback()
                err_msg = (
                    f"Failed to create relationship: connected memory records "
                    f"must exist in tenant: {exc}"
                )
                raise RepositoryError(err_msg) from exc

    async def get_relationships(
        self,
        tenant_id: str,
        memory_id: UUID,
        relation_type: RelationType | None = None,
    ) -> Sequence[MemoryRelationship]:
        """Fetch all relationships connected to memory_id."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = select(MemoryRelationshipORM).where(
                MemoryRelationshipORM.tenant_id == clean_tenant,
                (MemoryRelationshipORM.source_id == memory_id)
                | (
                    (MemoryRelationshipORM.bidirectional.is_(True))
                    & (MemoryRelationshipORM.target_id == memory_id)
                ),
            )
            if relation_type is not None:
                stmt = stmt.where(MemoryRelationshipORM.relation_type == relation_type.value)

            edges = (await session.execute(stmt)).scalars().all()
            return [orm_to_relationship(e) for e in edges]

    # -----------------------------------------------------------------------
    # Version History & Metadata Search
    # -----------------------------------------------------------------------

    async def get_memory_history(
        self, tenant_id: str, memory_id: UUID
    ) -> Sequence[Mapping[str, Any]]:
        """Retrieve audit version history for a memory record."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = (
                select(MemoryVersionHistoryORM)
                .where(
                    MemoryVersionHistoryORM.tenant_id == clean_tenant,
                    MemoryVersionHistoryORM.memory_id == memory_id,
                )
                .order_by(MemoryVersionHistoryORM.version.asc())
            )
            history_rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "history_id": str(h.history_id),
                    "memory_id": str(h.memory_id),
                    "version": h.version,
                    "original_content": h.original_content,
                    "normalized_content": h.normalized_content,
                    "status": h.status,
                    "metadata": h.metadata_payload,
                    "changed_at": h.changed_at.isoformat(),
                    "changed_by": h.changed_by,
                    "change_reason": h.change_reason,
                }
                for h in history_rows
            ]

    async def get_memory_events(self, tenant_id: str, memory_id: UUID) -> Sequence[MemoryEvent]:
        """Retrieve domain events recorded for a memory record."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = (
                select(MemoryEventORM)
                .where(
                    MemoryEventORM.tenant_id == clean_tenant,
                    MemoryEventORM.memory_id == memory_id,
                )
                .order_by(MemoryEventORM.timestamp.asc())
            )
            event_rows = (await session.execute(stmt)).scalars().all()
            return [orm_to_event(e) for e in event_rows]

    async def search_metadata(
        self, tenant_id: str, key_path: Sequence[str], expected_value: Any
    ) -> Sequence[MemoryRecord]:
        """Query memory records matching JSONB metadata criteria."""
        clean_tenant = tenant_id.strip()
        async with self.db.session(tenant_id=clean_tenant) as session:
            # Build JSONB containment dict: e.g. ["a", "b"] -> {"a": {"b": val}}
            nested_dict: dict[str, Any] = {}
            curr = nested_dict
            for i, k in enumerate(key_path):
                if i == len(key_path) - 1:
                    curr[k] = expected_value
                else:
                    curr[k] = {}
                    curr = curr[k]

            stmt = select(MemoryRecordORM).where(
                MemoryRecordORM.tenant_id == clean_tenant,
                MemoryRecordORM.status != LifecycleStatus.TOMBSTONED.value,
                MemoryRecordORM.metadata_payload.contains(nested_dict),
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [orm_to_memory_record(r) for r in rows]

    # -----------------------------------------------------------------------
    # Advanced Hybrid Querying (Dense Vector + Temporal + Lexical)
    # -----------------------------------------------------------------------

    async def query(self, spec: QuerySpec) -> Sequence[MemoryRecord]:
        """Execute composite search across pgvector distance, temporal bounds, and metadata."""
        clean_tenant = spec.filter.tenant_id.strip()
        q_filter = spec.filter

        async with self.db.session(tenant_id=clean_tenant) as session:
            stmt = select(MemoryRecordORM).where(MemoryRecordORM.tenant_id == clean_tenant)

            # Namespace filter
            if q_filter.namespace is not None:
                stmt = stmt.where(MemoryRecordORM.namespace == q_filter.namespace)

            # Tombstone filter
            if not spec.include_tombstoned:
                stmt = stmt.where(MemoryRecordORM.status != LifecycleStatus.TOMBSTONED.value)

            # Statuses
            if q_filter.statuses:
                stmt = stmt.where(MemoryRecordORM.status.in_([s.value for s in q_filter.statuses]))

            # Memory types
            if q_filter.memory_types:
                stmt = stmt.where(
                    MemoryRecordORM.memory_type.in_([m.value for m in q_filter.memory_types])
                )

            # Confidence and Importance bounds
            if spec.min_confidence > 0.0:
                stmt = stmt.where(MemoryRecordORM.confidence >= spec.min_confidence)
            if spec.min_importance > 0.0:
                stmt = stmt.where(MemoryRecordORM.importance >= spec.min_importance)

            # Temporal validity filter
            ref_time = q_filter.valid_at or q_filter.reference_time
            if ref_time is not None:
                stmt = stmt.where(
                    MemoryRecordORM.valid_from <= ref_time,
                    (MemoryRecordORM.valid_to.is_(None)) | (MemoryRecordORM.valid_to > ref_time),
                )

            # Created range
            if q_filter.created_after is not None:
                stmt = stmt.where(MemoryRecordORM.created_at >= q_filter.created_after)
            if q_filter.created_before is not None:
                stmt = stmt.where(MemoryRecordORM.created_at <= q_filter.created_before)

            # Provenance filters
            if q_filter.author_id is not None:
                stmt = stmt.where(MemoryRecordORM.author_id == q_filter.author_id)
            if q_filter.session_id is not None:
                stmt = stmt.where(MemoryRecordORM.session_id == q_filter.session_id)
            if q_filter.source_id is not None:
                stmt = stmt.where(MemoryRecordORM.source_id == q_filter.source_id)

            # Metadata containment
            if q_filter.metadata_filter:
                stmt = stmt.where(
                    MemoryRecordORM.metadata_payload.contains(dict(q_filter.metadata_filter))
                )

            # Dense Vector Search (pgvector L2 or cosine distance)
            if spec.query_vector is not None:
                # pgvector cosine distance: embedding.cosine_distance(spec.query_vector)
                distance_expr = MemoryRecordORM.embedding.cosine_distance(list(spec.query_vector))
                stmt = stmt.order_by(distance_expr.asc())
            elif spec.query_text:
                q_text = spec.query_text.strip()
                stmt = stmt.where(MemoryRecordORM.normalized_content.ilike(f"%{q_text}%"))
                stmt = stmt.order_by(MemoryRecordORM.created_at.desc())
            else:
                stmt = stmt.order_by(MemoryRecordORM.created_at.desc())

            stmt = stmt.limit(spec.top_k)
            rows = (await session.execute(stmt)).scalars().all()
            return [orm_to_memory_record(r) for r in rows]
