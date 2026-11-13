"""Type definitions, configuration models, and audit structures for AMARA lifecycle management."""

from __future__ import annotations

import datetime
import enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import LifecycleStatus
from amara.models.record import MemoryRecord


class LifecycleAction(enum.StrEnum):
    """Actions performed within the cognitive lifecycle subsystem."""

    RETAIN = "retain"
    UPDATE = "update"
    CONSOLIDATE = "consolidate"
    ARCHIVE = "archive"
    RESTORE = "restore"
    EXPIRE = "expire"
    DELETE = "delete"
    REINFORCE = "reinforce"
    DECAY = "decay"


class RetentionPolicy(BaseModel):
    """Configurable policy parameters governing retention, decay, and automated archival."""

    model_config = ConfigDict(frozen=True)

    max_age_days: float | None = Field(
        default=None,
        description="Maximum age in days before a record becomes eligible for cold archival.",
    )
    decay_half_life_days: float = Field(
        default=30.0,
        gt=0.0,
        description="Half-life parameter (T_1/2) in days for exponential recency decay.",
    )
    decay_activation_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Activation score threshold below which record transitions to DECAYING.",
    )
    archive_activation_threshold: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Activation score threshold below which record transitions to ARCHIVED.",
    )
    min_utility_threshold: float = Field(
        default=-2.0,
        description="Accumulated utility score below which decay is accelerated.",
    )
    critical_importance_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Importance score at or above which records are protected from decay.",
    )
    min_importance_threshold: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Importance threshold below which low-salience records decay rapidly.",
    )
    auto_archive_expired: bool = Field(
        default=True,
        description="Automatically transition temporally expired records to ARCHIVED status.",
    )
    respect_retention_locks: bool = Field(
        default=True,
        description="Protect records with retention_lock=True from automated decay/deletion.",
    )

    # Weights for multi-attribute activation calculation
    weight_recency: float = Field(default=0.30, ge=0.0, le=1.0)
    weight_importance: float = Field(default=0.35, ge=0.0, le=1.0)
    weight_utility: float = Field(default=0.20, ge=0.0, le=1.0)
    weight_frequency: float = Field(default=0.15, ge=0.0, le=1.0)


class ConsolidationPolicy(BaseModel):
    """Parameters governing duplicate detection, clustering, and semantic synthesis."""

    model_config = ConfigDict(frozen=True)

    similarity_threshold: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for near-duplicate clustering.",
    )
    lexical_overlap_threshold: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Token Jaccard overlap threshold for candidate clustering.",
    )
    min_cluster_size: int = Field(
        default=2,
        ge=2,
        description="Minimum number of related memories required to form a consolidation cluster.",
    )
    max_cluster_size: int = Field(
        default=10,
        ge=2,
        description="Maximum number of memories merged into a single consolidated semantic record.",
    )
    auto_transition_parents: bool = Field(
        default=True,
        description="Transition underlying parent records to CONSOLIDATED status upon synthesis.",
    )
    prevent_contradictory_merge: bool = Field(
        default=True,
        description="Refuse to consolidate any cluster containing contradictory propositions.",
    )


class LifecycleAuditRecord(BaseModel):
    """Immutable audit record logging each cognitive lifecycle action taken."""

    model_config = ConfigDict(frozen=True)

    memory_id: UUID
    tenant_id: str
    namespace: str
    action: LifecycleAction
    previous_status: LifecycleStatus
    new_status: LifecycleStatus
    reason: str
    performed_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    details: dict[str, Any] = Field(default_factory=dict)


class LifecycleEvaluationResult(BaseModel):
    """Result of multi-attribute policy evaluation on a memory record."""

    model_config = ConfigDict(frozen=True)

    memory_id: UUID
    current_status: LifecycleStatus
    recommended_action: LifecycleAction
    target_status: LifecycleStatus
    activation_score: float
    recency_score: float
    utility_score: float
    importance_score: float
    confidence_score: float
    access_count: int
    is_retention_locked: bool
    is_temporally_expired: bool
    rationale: str


class ConsolidationCandidate(BaseModel):
    """Identified cluster of near-duplicate or related memories eligible for synthesis."""

    model_config = ConfigDict(frozen=True)

    cluster_id: str
    tenant_id: str
    namespace: str
    memory_ids: tuple[UUID, ...]
    proposed_content: str
    combined_confidence: float
    max_importance: float
    source_ids: tuple[str, ...]
    evidence_count: int


class ConsolidationResult(BaseModel):
    """Outcome of a memory consolidation synthesis operation."""

    model_config = ConfigDict(frozen=True)

    consolidated_record: MemoryRecord
    parent_records: tuple[MemoryRecord, ...]
    created_relationship_ids: tuple[UUID, ...]


class ExpirationResult(BaseModel):
    """Summary of a TTL / temporal expiration scan cycle."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    namespace: str | None
    scanned_count: int
    expired_count: int
    archived_count: int
    protected_by_lock_count: int
    affected_memory_ids: tuple[UUID, ...]
