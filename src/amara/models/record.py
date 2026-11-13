"""Unified MemoryRecord domain model for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    ProvenanceSourceType,
)
from amara.exceptions import InvalidMemoryStateError, MemoryValidationError
from amara.models.evidence import MemoryEvidence
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity, validate_utc


def normalize_text(text: str) -> str:
    """Normalize whitespace and strip leading/trailing whitespace."""
    lines = [line.strip() for line in text.strip().splitlines()]
    return "\n".join(" ".join(line.split()) for line in lines if line)


# Legal state transitions in the cognitive lifecycle state machine
LEGAL_TRANSITIONS: Mapping[LifecycleStatus, set[LifecycleStatus]] = {
    LifecycleStatus.ACTIVE: {
        LifecycleStatus.ACTIVE,
        LifecycleStatus.DECAYING,
        LifecycleStatus.CONSOLIDATED,
        LifecycleStatus.SUPERSEDED,
        LifecycleStatus.ARCHIVED,
        LifecycleStatus.TOMBSTONED,
    },
    LifecycleStatus.DECAYING: {
        LifecycleStatus.ACTIVE,
        LifecycleStatus.DECAYING,
        LifecycleStatus.CONSOLIDATED,
        LifecycleStatus.SUPERSEDED,
        LifecycleStatus.ARCHIVED,
        LifecycleStatus.TOMBSTONED,
    },
    LifecycleStatus.CONSOLIDATED: {
        LifecycleStatus.CONSOLIDATED,
        LifecycleStatus.SUPERSEDED,
        LifecycleStatus.ARCHIVED,
        LifecycleStatus.TOMBSTONED,
    },
    LifecycleStatus.SUPERSEDED: {
        LifecycleStatus.SUPERSEDED,
        LifecycleStatus.ARCHIVED,
        LifecycleStatus.TOMBSTONED,
    },
    LifecycleStatus.ARCHIVED: {
        LifecycleStatus.ARCHIVED,
        LifecycleStatus.TOMBSTONED,
    },
    LifecycleStatus.TOMBSTONED: {
        LifecycleStatus.TOMBSTONED,
    },
}


class MemoryRecord(BaseModel):
    """The unified, strongly-typed memory record for AMARA."""

    model_config = ConfigDict(frozen=False, validate_assignment=True)

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique memory identifier.")
    tenant_id: str = Field(min_length=1, description="Enterprise tenant scope for isolation.")
    namespace: str = Field(
        default="default", min_length=1, description="Namespace or partition scope."
    )

    # Classification
    memory_type: MemoryCategory = Field(description="Cognitive memory category.")
    status: LifecycleStatus = Field(default=LifecycleStatus.ACTIVE, description="Lifecycle status.")

    # Content
    original_content: str = Field(min_length=1, description="Raw input text as ingested.")
    normalized_content: str = Field(
        min_length=1, description="Normalized representation for indexing."
    )

    # Provenance & Evidence
    source: MemorySource = Field(description="Source attribution and provenance tracking.")
    evidence: tuple[MemoryEvidence, ...] = Field(
        default_factory=tuple,
        description="Corroborating evidence grounding this memory.",
    )

    # Cognitive Qualities
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence score (0.0=uncertain, 1.0=certain).",
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Salience or intrinsic importance (0.0=ephemeral, 1.0=critical).",
    )

    # Temporal & Lineage
    temporal: TemporalValidity = Field(description="Bitemporal validity window.")
    version: int = Field(default=1, ge=1, description="Monotonically increasing version counter.")
    root_id: UUID = Field(description="Root ancestor memory ID in derivation tree.")
    parent_ids: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Immediate parent memory IDs that derived this record.",
    )

    # Vector Representation
    embedding: Sequence[float] | None = Field(
        default=None,
        description="Dense semantic vector embedding.",
    )
    embedding_model_id: str | None = Field(
        default=None,
        description="Identifier of the embedding model that generated the vector.",
    )

    # Metadata & Tracking
    metadata: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Modality-specific structured payloads or tags.",
    )
    access_count: int = Field(
        default=0, ge=0, description="Number of times retrieved and accessed."
    )
    utility_score: float = Field(
        default=0.0, description="Accumulated reinforcement utility score."
    )
    last_accessed_at: datetime.datetime | None = Field(
        default=None,
        description="Timestamp when last retrieved and incorporated into context.",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Record insertion timestamp in UTC.",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Record last modification timestamp in UTC.",
    )

    @field_validator("tenant_id", "namespace")
    @classmethod
    def _val_clean_strings(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("Field cannot be empty or whitespace.")
        return v_clean

    @field_validator("original_content", "normalized_content")
    @classmethod
    def _val_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content cannot be empty or whitespace.")
        return v

    @field_validator("created_at", "updated_at", "last_accessed_at")
    @classmethod
    def _val_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return validate_utc(v)

    @property
    def is_active(self) -> bool:
        """Return True if record is in ACTIVE lifecycle status."""
        return self.status == LifecycleStatus.ACTIVE

    @property
    def is_tombstoned(self) -> bool:
        """Return True if record has been soft-deleted / tombstoned."""
        return self.status == LifecycleStatus.TOMBSTONED

    def is_valid_at(self, reference_time: datetime.datetime) -> bool:
        """Check whether record is temporally valid at reference time."""
        return self.temporal.is_valid_at(reference_time)

    # -----------------------------------------------------------------------
    # Controlled Update Methods
    # -----------------------------------------------------------------------

    def update_content(
        self,
        new_content: str,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        """Controlled update of memory content, updating normalized content and version."""
        if not new_content or not new_content.strip():
            raise MemoryValidationError("new_content", "Cannot update memory to empty content.")
        now = updated_at or datetime.datetime.now(datetime.UTC)
        validate_utc(now, "updated_at")

        self.original_content = new_content
        self.normalized_content = normalize_text(new_content)
        self.version += 1
        self.updated_at = now

    def update_status(
        self,
        new_status: LifecycleStatus,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        """Transition record status following state machine transition rules."""
        if new_status not in LEGAL_TRANSITIONS.get(self.status, set()):
            raise InvalidMemoryStateError(self.status.value, new_status.value)
        now = updated_at or datetime.datetime.now(datetime.UTC)
        validate_utc(now, "updated_at")

        self.status = new_status
        self.updated_at = now

    def record_access(
        self,
        utility_delta: float = 0.0,
        accessed_at: datetime.datetime | None = None,
    ) -> None:
        """Record a retrieval access event, updating access count and utility reinforcement."""
        now = accessed_at or datetime.datetime.now(datetime.UTC)
        validate_utc(now, "accessed_at")

        self.access_count += 1
        self.last_accessed_at = now
        self.utility_score += utility_delta
        self.updated_at = now

    def add_evidence(
        self,
        evidence: MemoryEvidence,
        updated_at: datetime.datetime | None = None,
    ) -> None:
        """Attach corroborating evidence to this memory record."""
        now = updated_at or datetime.datetime.now(datetime.UTC)
        validate_utc(now, "updated_at")

        self.evidence = (*self.evidence, evidence)
        self.updated_at = now

    def soft_delete(self, deleted_at: datetime.datetime | None = None) -> None:
        """Transition record to TOMBSTONED lifecycle status."""
        self.update_status(LifecycleStatus.TOMBSTONED, updated_at=deleted_at)

    # -----------------------------------------------------------------------
    # Factory Methods
    # -----------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        tenant_id: str,
        content: str,
        memory_type: MemoryCategory,
        author_id: str,
        source_type: ProvenanceSourceType = ProvenanceSourceType.USER_INPUT,
        namespace: str = "default",
        confidence: float = 1.0,
        importance: float = 0.5,
        asserted_at: datetime.datetime | None = None,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        session_id: str | None = None,
        source_id: str | None = None,
        evidence: Sequence[MemoryEvidence] | None = None,
        embedding: Sequence[float] | None = None,
        embedding_model_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        parent_ids: Sequence[UUID] | None = None,
        root_id: UUID | None = None,
        memory_id: UUID | None = None,
    ) -> MemoryRecord:
        """Create a new validated MemoryRecord with automatic normalization and provenance."""
        now = datetime.datetime.now(datetime.UTC)
        effective_id = memory_id or uuid4()
        effective_asserted = asserted_at or now
        effective_valid_from = valid_from or effective_asserted

        validate_utc(effective_asserted, "asserted_at")
        validate_utc(effective_valid_from, "valid_from")
        validate_utc(valid_to, "valid_to")

        clean_original = content.strip()
        if not clean_original:
            raise MemoryValidationError("content", "Memory content cannot be empty.")

        clean_normalized = normalize_text(clean_original)

        parents_tuple = tuple(parent_ids) if parent_ids else ()
        effective_root_id = root_id or (parents_tuple[0] if parents_tuple else effective_id)

        source = MemorySource.create(
            source_id=source_id or f"src_{effective_id}",
            source_type=source_type,
            author_id=author_id,
            content=clean_original,
            session_id=session_id,
            asserted_at=effective_asserted,
        )

        temporal = TemporalValidity(
            asserted_at=effective_asserted,
            valid_from=effective_valid_from,
            valid_to=valid_to,
        )

        return cls(
            id=effective_id,
            tenant_id=tenant_id,
            namespace=namespace,
            memory_type=memory_type,
            status=LifecycleStatus.ACTIVE,
            original_content=clean_original,
            normalized_content=clean_normalized,
            source=source,
            evidence=tuple(evidence) if evidence else (),
            confidence=confidence,
            importance=importance,
            temporal=temporal,
            version=1,
            root_id=effective_root_id,
            parent_ids=parents_tuple,
            embedding=embedding,
            embedding_model_id=embedding_model_id,
            metadata=dict(metadata or {}),
            created_at=now,
            updated_at=now,
        )
