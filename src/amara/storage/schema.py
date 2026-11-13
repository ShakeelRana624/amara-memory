"""SQLAlchemy 2.x Declarative ORM schemas for AMARA PostgreSQL storage."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for AMARA PostgreSQL persistence."""


class MemoryRecordORM(Base):
    """PostgreSQL ORM mapping for MemoryRecord."""

    __tablename__ = "memory_records"

    # Primary Identity
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(
        String(128), nullable=False, default="default", index=True
    )

    # Classification
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)

    # Content
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)

    # Source Attribution & Provenance
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Cognitive Qualities
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Temporal Validity
    asserted_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Lineage & Versioning
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    root_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    parent_ids: Mapped[list[UUID]] = mapped_column(
        PG_ARRAY(PG_UUID(as_uuid=True)), nullable=False, default=list
    )

    # Vector Representation (pgvector 1536-dim standard)
    embedding: Mapped[Sequence[float] | None] = mapped_column(Vector(1536), nullable=True)
    embedding_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Structured Payloads
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    evidence_payload: Mapped[list[dict[str, Any]]] = mapped_column(
        "evidence", JSONB, nullable=False, default=list
    )

    # Cognitive Metrics & Usage
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    utility_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_accessed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # System Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    history_records: Mapped[list[MemoryVersionHistoryORM]] = relationship(
        "MemoryVersionHistoryORM",
        back_populates="memory_record",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_memory_tenant_modality", "tenant_id", "namespace", "memory_type", "status"),
        Index("idx_memory_temporal", "tenant_id", "valid_from", "valid_to"),
        Index("idx_memory_metadata_gin", "metadata", postgresql_using="gin"),
    )


class MemoryRelationshipORM(Base):
    """PostgreSQL ORM mapping for MemoryRelationship."""

    __tablename__ = "memory_relationships"

    relationship_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("memory_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("memory_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    bidirectional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_rel_tenant_source", "tenant_id", "source_id", "relation_type"),
        Index("idx_rel_tenant_target", "tenant_id", "target_id", "relation_type"),
    )


class MemoryVersionHistoryORM(Base):
    """PostgreSQL ORM mapping for memory audit history and past versions."""

    __tablename__ = "memory_version_history"

    history_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    memory_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("memory_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    changed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    memory_record: Mapped[MemoryRecordORM] = relationship(
        "MemoryRecordORM", back_populates="history_records"
    )

    __table_args__ = (
        Index("idx_history_tenant_memory_version", "tenant_id", "memory_id", "version"),
    )


class MemoryEventORM(Base):
    """PostgreSQL ORM mapping for domain events."""

    __tablename__ = "memory_events"

    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    namespace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    memory_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("idx_events_tenant_timestamp", "tenant_id", "timestamp"),
        Index("idx_events_tenant_memory", "tenant_id", "memory_id"),
    )
