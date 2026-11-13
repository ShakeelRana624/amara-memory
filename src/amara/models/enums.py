"""Enumerations defining memory modalities, states, and lifecycle stages."""

from __future__ import annotations

import enum


class MemoryModality(enum.StrEnum):
    """The four cognitive memory modalities supported by AMARA."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryState(enum.StrEnum):
    """The lifecycle state of a memory record."""

    ACTIVE = "active"
    DECAYING = "decaying"
    CONSOLIDATED = "consolidated"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    TOMBSTONED = "tombstoned"


class SalienceLevel(enum.StrEnum):
    """Qualitative salience thresholds for cognitive prioritization."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EPHEMERAL = "ephemeral"
