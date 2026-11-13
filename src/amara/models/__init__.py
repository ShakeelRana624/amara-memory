"""AMARA Core Domain Models.

Provides strongly-typed, Pydantic v2-validated representations of all cognitive
memory constructs, provenance metadata, temporal intervals, and graph relationships.
"""

from __future__ import annotations

from amara.enums import (
    DerivationType,
    LifecycleStatus,
    MemoryCategory,
    MemoryEventType,
    MemoryModality,
    MemoryState,
    MemoryType,
    ProvenanceSourceType,
    RelationType,
    SalienceLevel,
)
from amara.models.event import MemoryEvent
from amara.models.evidence import MemoryEvidence
from amara.models.projections import (
    ConceptPayload,
    EpisodePayload,
    ExecutionStep,
    ProceduralSkillPayload,
    SemanticTriple,
    WorkingMemoryItem,
)
from amara.models.record import MemoryRecord, normalize_text
from amara.models.relationship import MemoryRelationship
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity, validate_utc

__all__ = [
    "ConceptPayload",
    "DerivationType",
    "EpisodePayload",
    "ExecutionStep",
    "LifecycleStatus",
    "MemoryCategory",
    "MemoryEvent",
    "MemoryEventType",
    "MemoryEvidence",
    "MemoryModality",
    "MemoryRecord",
    "MemoryRelationship",
    "MemorySource",
    "MemoryState",
    "MemoryType",
    "ProceduralSkillPayload",
    "ProvenanceSourceType",
    "RelationType",
    "SalienceLevel",
    "SemanticTriple",
    "TemporalValidity",
    "WorkingMemoryItem",
    "normalize_text",
    "validate_utc",
]
