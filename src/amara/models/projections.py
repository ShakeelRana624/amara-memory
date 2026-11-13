"""Specialized cognitive projection models for memory modalities."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkingMemoryItem(BaseModel):
    """Projection representing an active scratchpad item or immediate attention focus."""

    model_config = ConfigDict(frozen=True)

    record_id: UUID
    content: str
    priority: int = Field(default=0, description="Priority rank in working memory buffer.")
    attention_focus: str | None = Field(default=None, description="Current sub-task or focus tag.")
    cache_coordinate: str | None = Field(
        default=None,
        description="Prefix hash coordinate for future compute / KV-cache reuse.",
    )


class EpisodePayload(BaseModel):
    """Structured payload for an episodic interaction event."""

    model_config = ConfigDict(frozen=True)

    actor: str = Field(description="Actor initiating the event (e.g. 'user', 'agent', 'tool').")
    action_type: str = Field(
        description="Type of action (e.g. 'utterance', 'tool_call', 'observation')."
    )
    observation: str | None = Field(
        default=None,
        description="Observed outcome or environment response.",
    )
    dialogue_turn: int | None = Field(default=None, description="Turn index within session.")
    causal_predecessor_id: UUID | None = Field(
        default=None, description="Preceding episode that caused this event."
    )


class SemanticTriple(BaseModel):
    """Atomic subject-predicate-object knowledge triple."""

    model_config = ConfigDict(frozen=True)

    subject: str
    predicate: str
    object: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    attributes: Mapping[str, Any] = Field(default_factory=dict)


class ConceptPayload(BaseModel):
    """Structured payload for a consolidated semantic concept node."""

    model_config = ConfigDict(frozen=True)

    concept_name: str
    category: str
    description: str
    triples: tuple[SemanticTriple, ...] = Field(default_factory=tuple)
    aliases: tuple[str, ...] = Field(default_factory=tuple)


class ExecutionStep(BaseModel):
    """A discrete operational step in a procedural skill."""

    model_config = ConfigDict(frozen=True)

    step_number: int
    tool_name: str
    parameters_template: Mapping[str, Any] = Field(default_factory=dict)
    expected_output_type: str | None = None
    fallback_step_number: int | None = None


class ProceduralSkillPayload(BaseModel):
    """Structured payload for an executable procedural skill or routine."""

    model_config = ConfigDict(frozen=True)

    skill_name: str
    description: str
    preconditions: tuple[str, ...] = Field(default_factory=tuple)
    parameters_schema: Mapping[str, Any] = Field(default_factory=dict)
    steps: tuple[ExecutionStep, ...] = Field(default_factory=tuple)
    success_criteria: str | None = None
    failure_recovery_rules: Sequence[str] = Field(default_factory=tuple)
