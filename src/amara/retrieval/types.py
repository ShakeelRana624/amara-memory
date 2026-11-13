"""Data structures and type definitions for AMARA memory retrieval engine."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import LifecycleStatus, MemoryCategory
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.models.temporal import TemporalValidity


class RetrievalStrategy(StrEnum):
    """Supported retrieval methodologies in AMARA."""

    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    TEMPORAL = "temporal"
    RELATIONAL = "relational"
    HYBRID = "hybrid"


class QueryIntent(StrEnum):
    """Categorized cognitive intent behind a search or retrieval query."""

    FACT_LOOKUP = "fact_lookup"
    PROCEDURAL_GUIDANCE = "procedural_guidance"
    TEMPORAL_HISTORY = "temporal_history"
    PREFERENCE_CHECK = "preference_check"
    GENERAL_REASONING = "general_reasoning"


class RetrievalWeights(BaseModel):
    """Relative channel weights for hybrid candidate combination."""

    model_config = ConfigDict(frozen=True)

    semantic: float = Field(default=0.50, ge=0.0, le=1.0)
    lexical: float = Field(default=0.25, ge=0.0, le=1.0)
    temporal: float = Field(default=0.15, ge=0.0, le=1.0)
    relational: float = Field(default=0.10, ge=0.0, le=1.0)

    def normalized(self) -> RetrievalWeights:
        """Return unit-normalized weights summing to 1.0."""
        total = self.semantic + self.lexical + self.temporal + self.relational
        if total == 0.0:
            return RetrievalWeights(semantic=0.5, lexical=0.25, temporal=0.15, relational=0.10)
        return RetrievalWeights(
            semantic=round(self.semantic / total, 4),
            lexical=round(self.lexical / total, 4),
            temporal=round(self.temporal / total, 4),
            relational=round(self.relational / total, 4),
        )


class RerankWeights(BaseModel):
    """Relative factor weights for cognitive reranking."""

    model_config = ConfigDict(frozen=True)

    relevance: float = Field(default=0.60, ge=0.0, le=1.0)
    importance: float = Field(default=0.15, ge=0.0, le=1.0)
    recency: float = Field(default=0.15, ge=0.0, le=1.0)
    utility: float = Field(default=0.10, ge=0.0, le=1.0)


class NormalizedQuery(BaseModel):
    """Decomposed and analyzed query specification."""

    model_config = ConfigDict(frozen=True)

    original_text: str
    normalized_text: str
    intent: QueryIntent = QueryIntent.GENERAL_REASONING
    entities: Sequence[str] = Field(default_factory=tuple)
    attributes: Sequence[str] = Field(default_factory=tuple)
    keywords: Sequence[str] = Field(default_factory=tuple)
    reference_time: datetime.datetime | None = None
    valid_at: datetime.datetime | None = None
    time_range: tuple[datetime.datetime | None, datetime.datetime | None] | None = None
    include_historical: bool = False


class ScoredMemoryCandidate(BaseModel):
    """Internal candidate representation with channel-specific match metrics."""

    model_config = ConfigDict(frozen=True)

    record: MemoryRecord
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    semantic_score: float = Field(default=0.0, ge=0.0, le=1.0)
    lexical_score: float = Field(default=0.0, ge=0.0, le=1.0)
    temporal_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relational_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    match_explanation: str = ""


class MemorySearchResult(BaseModel):
    """Fully materialized, verified retrieval result returned to caller.

    Separates factual epistemic confidence from retrieval relevance score.
    """

    model_config = ConfigDict(frozen=True)

    memory_id: UUID
    memory_type: MemoryCategory
    content: str
    normalized_content: str
    source_id: str
    timestamp: datetime.datetime
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Epistemic certainty/factual confidence of the memory record.",
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Query retrieval relevance score (independent of factual confidence).",
    )
    temporal_validity: TemporalValidity
    lifecycle_status: LifecycleStatus
    relevant_relationships: Sequence[MemoryRelationship] = Field(default_factory=tuple)
    evidence: Sequence[MemoryEvidence] = Field(default_factory=tuple)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    match_explanation: str = ""


class RetrievalResponse(BaseModel):
    """Complete retrieval response envelope with telemetry and metadata."""

    model_config = ConfigDict(frozen=True)

    query: str
    strategy: RetrievalStrategy
    intent: QueryIntent
    results: Sequence[MemorySearchResult]
    total_candidates: int
    latency_ms: float = Field(ge=0.0)
    tenant_id: str
    namespace: str
