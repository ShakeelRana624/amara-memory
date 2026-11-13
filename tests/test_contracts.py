"""Tests for repository, event, and provider contracts and runtime protocols."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from uuid import UUID

from amara.contracts.event_bus import MemoryEventHandler, MemoryEventPublisher
from amara.contracts.providers import EmbeddingAdapterProtocol, ExtractionAdapterProtocol
from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus, MemoryCategory, MemoryEventType, RelationType
from amara.models.event import MemoryEvent
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship


class MockMemoryRepository:
    """Mock implementation verifying protocol adherence."""

    async def initialize(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def store(self, _record: MemoryRecord) -> None:
        pass

    async def store_batch(self, _records: Sequence[MemoryRecord]) -> None:
        pass

    async def get_by_id(self, _tenant_id: str, _memory_id: UUID) -> MemoryRecord | None:
        return None

    async def query(self, _spec: QuerySpec) -> Sequence[MemoryRecord]:
        return []

    async def count(self, _tenant_id: str, _namespace: str | None = None) -> int:
        return 0

    async def update_status(
        self, _tenant_id: str, _memory_id: UUID, _status: LifecycleStatus
    ) -> None:
        pass

    async def update_metrics(
        self,
        _tenant_id: str,
        _memory_id: UUID,
        _utility_delta: float,
        _accessed_at: datetime.datetime,
    ) -> None:
        pass

    async def soft_delete(self, _tenant_id: str, _memory_id: UUID) -> bool:
        return True

    async def hard_delete(self, _tenant_id: str, _memory_id: UUID, _cascade: bool = False) -> int:
        return 1

    async def add_relationship(self, _relationship: MemoryRelationship) -> None:
        pass

    async def get_relationships(
        self,
        _tenant_id: str,
        _memory_id: UUID,
        _relation_type: RelationType | None = None,
    ) -> Sequence[MemoryRelationship]:
        return []

    async def create_memory(self, record: MemoryRecord) -> MemoryRecord:
        return record

    async def get_memory(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        return await self.get_by_id(tenant_id, memory_id)

    async def create_relationship(self, relationship: MemoryRelationship) -> MemoryRelationship:
        return relationship


class MockEventHandler:
    """Mock event consumer verifying protocol adherence."""

    async def handle(self, _event: MemoryEvent) -> None:
        pass


class MockEventPublisher:
    """Mock event publisher verifying protocol adherence."""

    async def publish(self, _event: MemoryEvent) -> None:
        pass

    def subscribe(self, _event_type: MemoryEventType, _handler: MemoryEventHandler) -> None:
        pass

    def unsubscribe(self, _event_type: MemoryEventType, _handler: MemoryEventHandler) -> None:
        pass


class MockEmbeddingAdapter:
    """Mock embedding generator verifying protocol adherence."""

    @property
    def dimension(self) -> int:
        return 1536

    @property
    def model_id(self) -> str:
        return "mock-embed-v1"

    async def embed_text(self, _text: str) -> Sequence[float]:
        return [0.1] * 1536

    async def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return [[0.1] * 1536 for _ in texts]


class MockExtractionAdapter:
    """Mock extraction engine verifying protocol adherence."""

    async def extract_facts(self, _text: str) -> Sequence[Mapping[str, str]]:
        return [{"subject": "user", "predicate": "likes", "object": "python"}]


def test_repository_protocol_runtime_check() -> None:
    """Verify MockMemoryRepository satisfies MemoryRepository protocol."""
    repo = MockMemoryRepository()
    assert isinstance(repo, MemoryRepository)


def test_event_contracts_runtime_check() -> None:
    """Verify event publisher and handler satisfy runtime protocols."""
    handler = MockEventHandler()
    publisher = MockEventPublisher()
    assert isinstance(handler, MemoryEventHandler)
    assert isinstance(publisher, MemoryEventPublisher)


def test_provider_contracts_runtime_check() -> None:
    """Verify provider adapters satisfy runtime protocols."""
    embedder = MockEmbeddingAdapter()
    extractor = MockExtractionAdapter()
    assert isinstance(embedder, EmbeddingAdapterProtocol)
    assert isinstance(extractor, ExtractionAdapterProtocol)


def test_query_spec_construction() -> None:
    """Verify QueryFilter and QuerySpec construction."""
    q_filter = QueryFilter(
        tenant_id="tenant_x",
        namespace="main",
        memory_types=[MemoryCategory.SEMANTIC, MemoryCategory.PROCEDURAL],
    )
    spec = QuerySpec(
        filter=q_filter,
        query_text="How to authenticate with API?",
        top_k=5,
    )

    assert spec.filter.tenant_id == "tenant_x"
    assert spec.filter.namespace == "main"
    assert spec.query_text == "How to authenticate with API?"
    assert spec.top_k == 5
