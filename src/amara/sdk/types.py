"""Public SDK data transfer objects and response models for AMARA."""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import LifecycleStatus, MemoryCategory
from amara.models.record import MemoryRecord


class MemoryItem(BaseModel):
    """Developer-friendly representation of a stored cognitive memory record."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    tenant_id: str
    namespace: str
    content: str
    normalized_content: str
    memory_type: MemoryCategory
    status: LifecycleStatus
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    source_id: str
    author_id: str
    session_id: str | None = None
    asserted_at: datetime.datetime
    valid_from: datetime.datetime
    valid_to: datetime.datetime | None = None
    version: int
    root_id: UUID
    parent_ids: tuple[UUID, ...]
    metadata: dict[str, Any]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_record(cls, record: MemoryRecord) -> MemoryItem:
        """Create a public MemoryItem from an internal domain MemoryRecord."""
        return cls(
            id=record.id,
            tenant_id=record.tenant_id,
            namespace=record.namespace,
            content=record.original_content,
            normalized_content=record.normalized_content,
            memory_type=record.memory_type,
            status=record.status,
            confidence=record.confidence,
            importance=record.importance,
            source_id=record.source.source_id,
            author_id=record.source.author_id,
            session_id=record.source.session_id,
            asserted_at=record.temporal.asserted_at,
            valid_from=record.temporal.valid_from,
            valid_to=record.temporal.valid_to,
            version=record.version,
            root_id=record.root_id,
            parent_ids=record.parent_ids,
            metadata=dict(record.metadata),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


class RecallItem(BaseModel):
    """Individual retrieved memory result paired with relevance score and explanation."""

    model_config = ConfigDict(frozen=True)

    item: MemoryItem
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    match_explanation: str = ""


class RecallResponse(BaseModel):
    """Response envelope for recall operations."""

    model_config = ConfigDict(frozen=True)

    query: str
    tenant_id: str
    namespace: str
    results: tuple[RecallItem, ...]
    total_candidates: int
    latency_ms: float = Field(ge=0.0)


class InspectionResult(BaseModel):
    """Detailed structural and relational inspection of a stored memory node."""

    model_config = ConfigDict(frozen=True)

    record: MemoryItem
    parents: tuple[MemoryItem, ...]
    relationships: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]


class EngineStats(BaseModel):
    """Cognitive distribution statistics for a tenant or namespace."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    namespace: str | None
    total_memories: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    average_confidence: float
    average_importance: float
