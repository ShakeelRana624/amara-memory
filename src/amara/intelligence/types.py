"""Data structures and types for the AMARA memory intelligence and extraction engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.models.record import MemoryRecord


class ExtractedEntity(BaseModel):
    """Named entity recognized from raw cognitive input."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, description="Entity surface name or canonical label.")
    entity_type: str = Field(
        min_length=1,
        description="Categorical entity type (e.g. PERSON, TECHNOLOGY, PREFERENCE, CONCEPT).",
    )
    start_char: int | None = Field(default=None, description="Starting character index in source.")
    end_char: int | None = Field(default=None, description="Ending character index in source.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence.")
    attributes: Mapping[str, Any] = Field(
        default_factory=dict, description="Extracted entity properties."
    )


class ExtractedFact(BaseModel):
    """Atomic knowledge proposition extracted from cognitive input."""

    model_config = ConfigDict(frozen=True)

    subject: str = Field(min_length=1, description="Subject entity.")
    predicate: str = Field(min_length=1, description="Relationship or property attribute.")
    object: str = Field(min_length=1, description="Target value or related entity.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Epistemic confidence.")
    is_negated: bool = Field(
        default=False, description="Whether the proposition is an explicit negation."
    )
    context_snippet: str | None = Field(default=None, description="Verbatim supporting sentence.")
    temporal_hint: str | None = Field(
        default=None, description="Temporal anchor if specified in text."
    )
    attributes: Mapping[str, Any] = Field(
        default_factory=dict, description="Supplementary fact metadata."
    )


class ExtractedSkill(BaseModel):
    """Procedural workflow or skill extracted from procedural text."""

    model_config = ConfigDict(frozen=True)

    skill_name: str = Field(min_length=1, description="Identifier or name of the procedural skill.")
    description: str = Field(min_length=1, description="Summary of skill purpose.")
    preconditions: tuple[str, ...] = Field(
        default_factory=tuple, description="Prerequisite conditions."
    )
    steps: tuple[str, ...] = Field(default_factory=tuple, description="Sequential action steps.")


class ContradictionCandidate(BaseModel):
    """Identified cognitive conflict between an incoming memory and an existing stored memory."""

    model_config = ConfigDict(frozen=True)

    existing_memory_id: UUID = Field(
        description="ID of the previously stored contradictory memory."
    )
    candidate_memory_id: UUID | None = Field(
        default=None, description="ID of the incoming contradictory candidate if generated."
    )
    entity: str = Field(description="Subject entity involved in conflict.")
    attribute: str = Field(description="Conflicting property or predicate.")
    existing_value: str = Field(description="Value asserted in the existing historical memory.")
    incoming_value: str = Field(description="New value asserted in the incoming candidate.")
    severity: str = Field(
        default="direct_conflict",
        description="Severity ('direct_conflict', 'temporal_evolution', 'confidence_divergence').",
    )
    temporal_relationship: str = Field(
        default="concurrent_conflict",
        description="Dynamic ('supersedes', 'concurrent_conflict', 'historical_divergence').",
    )
    confidence_delta: float = Field(
        default=0.0, description="Confidence difference (incoming - existing)."
    )
    status: str = Field(
        default="unresolved",
        description="Resolution status ('unresolved', 'superseded', 'review_required').",
    )
    resolution_rationale: str | None = Field(
        default=None, description="Audit rationale explaining how conflict was handled."
    )


class DeduplicationResult(BaseModel):
    """Outcome of duplicate detection analysis against existing repository memories."""

    model_config = ConfigDict(frozen=True)

    is_duplicate: bool = Field(description="Whether a duplicate memory was detected.")
    duplicate_memory_id: UUID | None = Field(
        default=None, description="Matching memory ID if found."
    )
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity metric.")
    match_type: str = Field(
        default="none",
        description="Matching mechanism ('exact_hash', 'exact_normalized', 'vector', 'none').",
    )
    action_taken: str = Field(
        default="create_new",
        description="Recommended action ('reinforce_existing', 'merge_evidence', 'create_new').",
    )


class IngestionCandidate(BaseModel):
    """An analyzed memory candidate prepared for routing, deduplication, and persistence."""

    model_config = ConfigDict(frozen=True)

    record: MemoryRecord = Field(description="Fully constructed MemoryRecord domain model.")
    source_input: str = Field(description="Original un-normalized input text.")
    facts: tuple[ExtractedFact, ...] = Field(
        default_factory=tuple, description="Extracted factual claims."
    )
    entities: tuple[ExtractedEntity, ...] = Field(
        default_factory=tuple, description="Extracted named entities."
    )
    deduplication_result: DeduplicationResult | None = Field(
        default=None, description="Deduplication analysis result."
    )
    contradictions: tuple[ContradictionCandidate, ...] = Field(
        default_factory=tuple, description="Identified contradiction candidates."
    )


class IngestionResult(BaseModel):
    """Final output summary of the memory ingestion and intelligence pipeline."""

    model_config = ConfigDict(frozen=True)

    stored_records: tuple[MemoryRecord, ...] = Field(
        default_factory=tuple, description="New memory records successfully persisted."
    )
    reinforced_records: tuple[UUID, ...] = Field(
        default_factory=tuple, description="Existing memory record IDs that were reinforced."
    )
    deduplicated_count: int = Field(
        default=0, ge=0, description="Count of duplicate items filtered."
    )
    contradictions_detected: tuple[ContradictionCandidate, ...] = Field(
        default_factory=tuple, description="All conflicting facts identified during ingestion."
    )
    created_relationships: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="IDs of relational edges (e.g. contradiction links) created.",
    )
