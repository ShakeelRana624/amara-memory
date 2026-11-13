# AMARA Data Model Specification: Unified Typed Schema & PostgreSQL DDL (v0.1)

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`system-design.md`](system-design.md), [`memory-lifecycle.md`](memory-lifecycle.md), [`security-model.md`](security-model.md)

---

## 1. Overview and Core Design Principles

AMARA unifies all cognitive memory modalities into a single, strongly-typed polymorphic record model: `MemoryRecord`. Specialized views (Working, Episodic, Semantic, Procedural) are structured projections of this unified schema.

Key characteristics:
1. **Pydantic v2 Validation**: Strict type enforcement, zero type coercion on ambiguous fields, JSON Schema compatibility.
2. **Strict UTC Timestamps**: All datetime fields require explicit timezone awareness set to `datetime.UTC`. Naive datetimes fail validation.
3. **Bitemporal Temporal Validity**: Every record cleanly distinguishes between transaction time (`created_at`) and world validity intervals ($[t_{valid\_from}, t_{valid\_to}]$).
4. **First-Class Provenance & Lineage**: Every memory carries its derivation lineage and cryptographic signature.
5. **Relational + Vector Hybrid**: PostgreSQL DDL utilizing `pgvector` for dense semantic embeddings and standard relational foreign keys/indexes for associative graphs.

---

## 2. Pydantic v2 Domain Models

```python
"""AMARA Core Domain Models (Pydantic v2 Specification)."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryModality(str, Enum):
    """The four primary cognitive memory modalities."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryState(str, Enum):
    """The lifecycle state of a memory record."""

    ACTIVE = "active"
    DECAYING = "decaying"
    CONSOLIDATED = "consolidated"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    TOMBSTONED = "tombstoned"


class ProvenanceSourceType(str, Enum):
    """Origin source type for memory provenance."""

    USER_INPUT = "user_input"
    AGENT_REASONING = "agent_reasoning"
    TOOL_EXECUTION = "tool_execution"
    ENVIRONMENT_PERCEPT = "environment_percept"
    CONSOLIDATION_SYNTHESIS = "consolidation_synthesis"
    SYSTEM_INSTRUCTION = "system_instruction"


class DerivationType(str, Enum):
    """Derivation relationship between a memory and its parents."""

    ROOT = "root"
    DIRECT_EXTRACTION = "direct_extraction"
    CONSOLIDATION_CLUSTER = "consolidation_cluster"
    CONTRADICTION_REVISION = "contradiction_revision"
    GENERALIZATION = "generalization"


class RelationType(str, Enum):
    """Relational association types between memory nodes."""

    CAUSAL = "causal"  # Episode A caused Episode B
    TEMPORAL_NEXT = "temporal_next"  # Episode B follows Episode A
    ENTITY_ATTRIBUTE = "entity_attr"  # Memory asserts attribute of entity
    CONTRADICTS = "contradicts"  # Memory A contradicts Memory B
    DEPENDS_ON = "depends_on"  # Skill requires prerequisite memory
    ASSOCIATED_WITH = "associated_with"  # Thematic/semantic co-occurrence


# ---------------------------------------------------------------------------
# Component Models
# ---------------------------------------------------------------------------


class TemporalValidity(BaseModel):
    """Bitemporal validity window modeling real-world truth."""

    model_config = ConfigDict(frozen=True)

    asserted_at: datetime.datetime = Field(
        description="When the event or fact occurred in the real world."
    )
    valid_from: datetime.datetime = Field(description="Start of temporal validity window.")
    valid_to: datetime.datetime | None = Field(
        default=None,
        description="End of temporal validity window (None represents unbounded future).",
    )

    @field_validator("asserted_at", "valid_from", "valid_to")
    @classmethod
    def ensure_utc(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        if v is not None and v.tzinfo != datetime.UTC:
            raise ValueError("All temporal validity timestamps must be timezone-aware UTC.")
        return v


class ProvenanceRecord(BaseModel):
    """Auditable provenance and origin metadata."""

    model_config = ConfigDict(frozen=True)

    source_type: ProvenanceSourceType
    author_id: str = Field(description="User ID, Agent ID, or Tool Name.")
    session_id: str | None = Field(default=None, description="Conversation or task session ID.")
    source_event_id: str | None = Field(default=None, description="Raw message or log identifier.")
    extractor_signature: str | None = Field(
        default=None, description="Model identifier or rule signature that extracted this memory."
    )
    content_hash: str = Field(description="SHA-256 hash of the content payload at ingestion.")


class LineageRecord(BaseModel):
    """Lineage DAG tracking parent-child memory derivations."""

    model_config = ConfigDict(frozen=True)

    root_id: UUID = Field(description="Root ancestor memory ID.")
    parent_ids: tuple[UUID, ...] = Field(
        default_factory=tuple, description="Immediate parent memory IDs that derived this record."
    )
    derivation_type: DerivationType = Field(default=DerivationType.ROOT)
    version: int = Field(default=1, ge=1, description="Monotonically increasing version counter.")


class CognitiveMetrics(BaseModel):
    """Dynamic cognitive scoring and retention metrics."""

    salience: float = Field(default=0.5, ge=0.0, le=1.0, description="Intrinsic importance.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Epistemic certainty.")
    utility_score: float = Field(default=0.0, description="Reinforcement score from task utility.")
    access_count: int = Field(default=0, ge=0, description="Number of times retrieved and used.")
    last_accessed_at: datetime.datetime | None = Field(
        default=None, description="Last time memory was retrieved and incorporated into context."
    )


class AssociationEdge(BaseModel):
    """Typed relational association link between two memories."""

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    relation_type: RelationType
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    bidirectional: bool = Field(default=False)
    metadata: Mapping[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Unified Memory Record
# ---------------------------------------------------------------------------


class MemoryRecord(BaseModel):
    """The unified, strongly-typed memory record for AMARA."""

    model_config = ConfigDict(frozen=False)

    id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(description="Enterprise tenant identifier for strict isolation.")
    namespace: str = Field(default="default", description="Agent namespace or partition scope.")
    modality: MemoryModality
    state: MemoryState = Field(default=MemoryState.ACTIVE)

    # Core Payloads
    content: str = Field(description="Human-readable text content or natural language assertion.")
    structured_payload: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Modality-specific structured data (e.g. concept triples, tool signatures).",
    )
    embedding: Sequence[float] | None = Field(
        default=None, description="Dense semantic vector embedding."
    )

    # Cognitive & Temporal Metadata
    temporal: TemporalValidity
    provenance: ProvenanceRecord
    lineage: LineageRecord
    metrics: CognitiveMetrics = Field(default_factory=CognitiveMetrics)

    # Technical Timestamps
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    deleted_at: datetime.datetime | None = Field(
        default=None, description="Timestamp of soft deletion / tombstoning."
    )

    @field_validator("created_at", "updated_at", "deleted_at")
    @classmethod
    def ensure_utc_timestamps(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        if v is not None and v.tzinfo != datetime.UTC:
            raise ValueError("All record timestamps must be timezone-aware UTC.")
        return v
```

---

## 3. PostgreSQL + pgvector DDL Specification

```sql
-- PostgreSQL 16+ Database Schema with pgvector
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- --------------------------------------------------------------------------
-- 1. Unified Memory Records Table
-- --------------------------------------------------------------------------
CREATE TABLE memory_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(128) NOT NULL,
    namespace VARCHAR(128) NOT NULL DEFAULT 'default',
    modality VARCHAR(32) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'active',
    
    -- Content & Vectors
    content TEXT NOT NULL,
    structured_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536), -- Standard embedding dimension (configurable per adapter)
    
    -- Bitemporal Validity
    asserted_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    
    -- Provenance & Lineage
    source_type VARCHAR(64) NOT NULL,
    author_id VARCHAR(128) NOT NULL,
    session_id VARCHAR(128),
    source_event_id VARCHAR(128),
    extractor_signature VARCHAR(128),
    content_hash CHAR(64) NOT NULL,
    root_id UUID NOT NULL,
    parent_ids UUID[] NOT NULL DEFAULT '{}',
    derivation_type VARCHAR(64) NOT NULL DEFAULT 'root',
    version INT NOT NULL DEFAULT 1,
    
    -- Cognitive Metrics
    salience REAL NOT NULL DEFAULT 0.5,
    confidence REAL NOT NULL DEFAULT 1.0,
    utility_score REAL NOT NULL DEFAULT 0.0,
    access_count INT NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    
    -- System Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Enable Row-Level Security for strict tenant isolation
ALTER TABLE memory_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON memory_records
    USING (tenant_id = current_setting('app.current_tenant_id', true));

-- --------------------------------------------------------------------------
-- 2. Indexes for High-Performance Hybrid Retrieval
-- --------------------------------------------------------------------------

-- HNSW Vector Index on Embeddings (Cosine Distance)
CREATE INDEX idx_memory_records_hnsw 
ON memory_records 
USING hnsw (embedding vector_cosine_ops)
WHERE deleted_at IS NULL AND state IN ('active', 'decaying');

-- Composite B-Tree Index for Tenant, Modality, and Temporal Validity
CREATE INDEX idx_memory_records_tenant_modality_temporal 
ON memory_records (tenant_id, namespace, modality, state, valid_from, valid_to)
WHERE deleted_at IS NULL;

-- Full-Text Search Index (GIN)
CREATE INDEX idx_memory_records_fts 
ON memory_records 
USING gin (to_tsvector('english', content))
WHERE deleted_at IS NULL;

-- GIN Index on Structured Payload
CREATE INDEX idx_memory_records_payload_gin 
ON memory_records 
USING gin (structured_payload jsonb_path_ops);

-- Provenance Root Lineage Index
CREATE INDEX idx_memory_records_root_id 
ON memory_records (tenant_id, root_id);

-- --------------------------------------------------------------------------
-- 3. Memory Associations Table (Graph Edges)
-- --------------------------------------------------------------------------
CREATE TABLE memory_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(128) NOT NULL,
    source_id UUID NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
    relation_type VARCHAR(64) NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    bidirectional BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE memory_associations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_associations_policy ON memory_associations
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE INDEX idx_associations_source 
ON memory_associations (tenant_id, source_id, relation_type);

CREATE INDEX idx_associations_target 
ON memory_associations (tenant_id, target_id, relation_type);
```
