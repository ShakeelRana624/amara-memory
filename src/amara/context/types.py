"""Type definitions and models for context reconstruction and token budgeting."""

from __future__ import annotations

import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import MemoryCategory


class ContextBudget(BaseModel):
    """Specification of token allocations for prompt construction."""

    model_config = ConfigDict(frozen=True)

    max_tokens: int = Field(
        default=2048,
        gt=0,
        description="Total token ceiling allocated for the reconstructed context block.",
    )
    system_reserved_tokens: int = Field(
        default=256,
        ge=0,
        description="Tokens reserved for system prompt headers and formatting boilerplate.",
    )
    min_tokens_per_item: int = Field(
        default=16,
        ge=1,
        description="Minimum token threshold required to pack an individual memory candidate.",
    )

    @property
    def available_memory_tokens(self) -> int:
        """Token budget available exclusively for memory candidates and citations."""
        return max(0, self.max_tokens - self.system_reserved_tokens)


class ContextCitation(BaseModel):
    """Structured citation metadata attributing a context claim to stored provenance."""

    model_config = ConfigDict(frozen=True)

    citation_index: int = Field(description="1-based citation index (e.g. 1 for [REF-1]).")
    citation_tag: str = Field(description="Formatted citation identifier, e.g. '[REF-1]'.")
    memory_id: UUID = Field(description="Primary key UUID of the source memory record.")
    source_id: str = Field(description="Origin source identifier from memory provenance.")
    author_id: str = Field(description="Origin author or agent identifier.")
    memory_type: MemoryCategory = Field(description="Cognitive memory category.")
    confidence: float = Field(description="Epistemic factual confidence score.")
    importance: float = Field(description="Intrinsic cognitive salience score.")
    asserted_at: datetime.datetime = Field(description="UTC timestamp when asserted.")
    valid_from: datetime.datetime = Field(description="UTC validity start.")
    valid_to: datetime.datetime | None = Field(
        default=None, description="UTC validity expiration if bounded."
    )
    temporal_anchor: str = Field(description="Human-readable temporal validity summary.")
    snippet: str = Field(description="Brief text summary of the cited claim.")


class PackedContextItem(BaseModel):
    """An individual memory record packed into the reconstructed context budget."""

    model_config = ConfigDict(frozen=True)

    citation_index: int
    citation_tag: str
    memory_id: UUID
    content: str
    token_count: int
    composite_rank_score: float
    temporal_anchor: str


class ContextReconstructionConfig(BaseModel):
    """Configuration options governing retrieval, ranking, redundancy removal, and formatting."""

    model_config = ConfigDict(frozen=True)

    abstention_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Relevance threshold below which insufficient evidence is signaled.",
    )
    redundancy_similarity_threshold: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0,
        description="Similarity threshold above which near-duplicate candidates are filtered out.",
    )
    citation_prefix: str = Field(
        default="REF",
        description="Prefix string used for citations (e.g. 'REF' produces '[REF-1]').",
    )
    include_temporal_anchors: bool = Field(
        default=True,
        description="Include explicit temporal stamps and validity bounds in citations.",
    )
    include_provenance_header: bool = Field(
        default=True,
        description="Prepend a markdown header block describing memory verification status.",
    )

    # Ranking weights
    weight_relevance: float = Field(default=0.60, ge=0.0, le=1.0)
    weight_confidence: float = Field(default=0.25, ge=0.0, le=1.0)
    weight_importance: float = Field(default=0.15, ge=0.0, le=1.0)


class ReconstructedContext(BaseModel):
    """The fully reconstructed, token-bounded context ready for LLM prompt assembly."""

    model_config = ConfigDict(frozen=True)

    query: str
    tenant_id: str
    namespace: str
    formatted_context: str
    citations: tuple[ContextCitation, ...]
    packed_items: tuple[PackedContextItem, ...]
    total_tokens_used: int
    remaining_token_budget: int
    abstention_recommended: bool
    abstention_reason: str | None
    candidates_retrieved: int
    candidates_packed: int
    candidates_omitted_budget: int
    candidates_omitted_redundant: int
    reconstructed_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
