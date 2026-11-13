"""Canonical enumerations for AMARA memory types, lifecycle statuses, and relations."""

from __future__ import annotations

import enum


class MemoryCategory(enum.StrEnum):
    """The foundational cognitive memory categories supported by AMARA."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    ASSOCIATIVE = "associative"


# Backward-compatible alias
MemoryType = MemoryCategory
MemoryModality = MemoryCategory


class LifecycleStatus(enum.StrEnum):
    """Lifecycle states of a memory record within the cognitive state machine."""

    ACTIVE = "active"
    DECAYING = "decaying"
    CONSOLIDATED = "consolidated"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    TOMBSTONED = "tombstoned"


# Backward-compatible alias
MemoryState = LifecycleStatus


class ProvenanceSourceType(enum.StrEnum):
    """Origin source classification for memory provenance."""

    USER_INPUT = "user_input"
    AGENT_REASONING = "agent_reasoning"
    TOOL_EXECUTION = "tool_execution"
    ENVIRONMENT_PERCEPT = "environment_percept"
    CONSOLIDATION_SYNTHESIS = "consolidation_synthesis"
    SYSTEM_INSTRUCTION = "system_instruction"


class DerivationType(enum.StrEnum):
    """Derivation relationship between a memory and its ancestor records."""

    ROOT = "root"
    DIRECT_EXTRACTION = "direct_extraction"
    CONSOLIDATION_CLUSTER = "consolidation_cluster"
    CONTRADICTION_REVISION = "contradiction_revision"
    GENERALIZATION = "generalization"


class RelationType(enum.StrEnum):
    """Relational association types between memory nodes in the associative graph."""

    CAUSAL = "causal"  # Event A caused Event B
    TEMPORAL_NEXT = "temporal_next"  # Event B chronologically follows Event A
    ENTITY_ATTRIBUTE = "entity_attr"  # Fact asserts attribute of an entity
    CONTRADICTS = "contradicts"  # Memory A contradicts Memory B
    DEPENDS_ON = "depends_on"  # Skill or action requires prerequisite memory
    ASSOCIATED_WITH = "associated_with"  # General thematic/associative link


class MemoryEventType(enum.StrEnum):
    """Domain event types emitted throughout the memory lifecycle."""

    CREATED = "memory.created"
    UPDATED = "memory.updated"
    ACCESSED = "memory.accessed"
    REINFORCED = "memory.reinforced"
    DECAYED = "memory.decayed"
    CONSOLIDATED = "memory.consolidated"
    SUPERSEDED = "memory.superseded"
    TOMBSTONED = "memory.tombstoned"
    PURGED = "memory.purged"


class SalienceLevel(enum.StrEnum):
    """Qualitative salience thresholds for cognitive prioritization."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EPHEMERAL = "ephemeral"
