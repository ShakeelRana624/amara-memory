"""Repository contract defining persistence and retrieval interfaces."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from amara.contracts.query import QuerySpec
from amara.enums import LifecycleStatus, RelationType
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship


@runtime_checkable
class MemoryRepository(Protocol):
    """Abstract persistence interface for memory storage backends."""

    async def initialize(self) -> None:
        """Initialize connection pools, verify schema migrations, and prepare indexes."""
        ...

    async def close(self) -> None:
        """Gracefully close connections and release storage resources."""
        ...

    async def store(self, record: MemoryRecord) -> None:
        """Persist a single memory record transactionally."""
        ...

    async def store_batch(self, records: Sequence[MemoryRecord]) -> None:
        """Persist a collection of memory records within an atomic transaction."""
        ...

    async def get_by_id(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Retrieve a specific memory record by its primary key within tenant scope."""
        ...

    async def query(self, spec: QuerySpec) -> Sequence[MemoryRecord]:
        """Execute a structured search and return matching memory records."""
        ...

    async def count(self, tenant_id: str, namespace: str | None = None) -> int:
        """Count active, non-tombstoned memory records within tenant scope."""
        ...

    async def update_status(self, tenant_id: str, memory_id: UUID, status: LifecycleStatus) -> None:
        """Transition a record to a new lifecycle status."""
        ...

    async def update_metrics(
        self,
        tenant_id: str,
        memory_id: UUID,
        utility_delta: float,
        accessed_at: datetime.datetime,
    ) -> None:
        """Increment access count and apply utility score reinforcement."""
        ...

    async def soft_delete(self, tenant_id: str, memory_id: UUID) -> bool:
        """Mark a memory record as TOMBSTONED, removing it from active queries."""
        ...

    async def hard_delete(self, tenant_id: str, memory_id: UUID, cascade: bool = False) -> int:
        """Permanently delete a record, optionally cascading along derivation lineages."""
        ...

    async def add_relationship(self, relationship: MemoryRelationship) -> None:
        """Create a relational association edge between two memory records."""
        ...

    async def get_relationships(
        self,
        tenant_id: str,
        memory_id: UUID,
        relation_type: RelationType | None = None,
    ) -> Sequence[MemoryRelationship]:
        """Retrieve association edges connected to the specified memory record."""
        ...

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
        ...

    async def create_memory(self, record: MemoryRecord) -> MemoryRecord:
        """Create and persist a new memory record (convenience alias for store)."""
        ...

    async def get_memory(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Retrieve a specific memory record by primary key (convenience alias for get_by_id)."""
        ...

    async def create_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        """Create a relational association edge (convenience alias for add_relationship)."""
        ...
