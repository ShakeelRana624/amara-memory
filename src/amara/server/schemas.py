"""Public REST API request and response data contracts for AMARA."""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.types import MemoryItem, RecallItem


class CreateMemoryRequest(BaseModel):
    """Payload for ingesting and storing a new cognitive memory."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, description="Raw text proposition or observation.")
    author_id: str = Field(default="user", description="Identifier of the asserting author/agent.")
    memory_type: MemoryCategory | None = Field(
        default=None, description="Optional target memory category."
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Epistemic factual confidence."
    )
    importance: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Intrinsic cognitive salience."
    )
    namespace: str = Field(default="default", description="Memory partition namespace.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Arbitrary structured tags.")
    session_id: str | None = Field(default=None, description="Optional session or thread context.")
    valid_from: datetime.datetime | None = Field(default=None, description="UTC validity start.")
    valid_to: datetime.datetime | None = Field(default=None, description="UTC validity expiration.")
    evidence: list[dict[str, Any]] | None = Field(
        default=None, description="Optional corroborating evidence."
    )


class UpdateMemoryRequest(BaseModel):
    """Payload for updating an existing memory record."""

    model_config = ConfigDict(extra="forbid")

    content: str | None = Field(default=None, min_length=1, description="Updated memory content.")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Metadata key-value updates to merge."
    )


class SearchMemoryRequest(BaseModel):
    """Payload for multi-channel hybrid memory search."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, description="Natural language search or reasoning query.")
    namespace: str = Field(default="default", description="Namespace scope.")
    strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.HYBRID, description="Retrieval strategy."
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum results to return.")
    memory_types: list[MemoryCategory] | None = Field(
        default=None, description="Filter by memory categories."
    )
    valid_at: datetime.datetime | None = Field(
        default=None, description="Temporal point-in-time filter."
    )
    include_historical: bool = Field(
        default=False, description="Whether to include superseded/archived records."
    )


class ConsolidateRequest(BaseModel):
    """Payload for triggering knowledge consolidation."""

    model_config = ConfigDict(extra="forbid")

    namespace: str = Field(default="default", description="Namespace to consolidate.")


class ReconstructContextRequest(BaseModel):
    """Payload for reconstructing a token-bounded context prompt."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, description="Prompt query to ground in retrieved context.")
    namespace: str = Field(default="default", description="Namespace scope.")
    budget_tokens: int = Field(
        default=2048, ge=64, le=32768, description="Maximum token allocation."
    )
    strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.HYBRID, description="Retrieval strategy."
    )


class CreateAPIKeyRequest(BaseModel):
    """Payload for generating a new tenant API key."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Default Key", description="Human-readable label for key.")
    workspace_id: str | None = Field(default=None, description="Optional workspace partition.")
    scopes: list[str] = Field(
        default=["read", "write"], description="Authorized permission scopes."
    )
    expires_in_days: float | None = Field(
        default=None, gt=0, description="Optional lifespan in days."
    )


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class MemoryResponse(BaseModel):
    """Standard public response envelope for a memory record."""

    model_config = ConfigDict(frozen=True)

    data: MemoryItem


class SearchResponse(BaseModel):
    """Response envelope for search results."""

    model_config = ConfigDict(frozen=True)

    query: str
    tenant_id: str
    namespace: str
    results: list[RecallItem]
    total_candidates: int
    latency_ms: float


class ConsolidateResponse(BaseModel):
    """Response envelope for consolidation operations."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    namespace: str
    consolidated_count: int
    new_semantic_memories: list[MemoryItem]


class CitationItem(BaseModel):
    """Structured citation representation for reconstructed context."""

    model_config = ConfigDict(frozen=True)

    citation_tag: str
    memory_id: UUID
    source_id: str
    author_id: str
    confidence: float
    importance: float
    temporal_anchor: str
    snippet: str


class ReconstructResponse(BaseModel):
    """Structured response for reconstructed context."""

    model_config = ConfigDict(frozen=True)

    query: str
    formatted_context: str
    citations: list[CitationItem]
    total_tokens_used: int
    remaining_token_budget: int
    abstention_recommended: bool
    abstention_reason: str | None
    candidates_retrieved: int
    candidates_packed: int


class UsageResponse(BaseModel):
    """Usage statistics response for authorized tenant."""

    model_config = ConfigDict(frozen=True)

    tenant_id: str
    namespace: str | None
    total_memories: int
    by_category: dict[str, int]
    by_status: dict[str, int]
    average_confidence: float
    average_importance: float


class HealthResponse(BaseModel):
    """System health check and diagnostic status."""

    model_config = ConfigDict(frozen=True)

    status: str = "healthy"
    version: str
    storage_backend: str
    database_connected: bool
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class APIKeyCreatedResponse(BaseModel):
    """Response when a new key is created, containing the single-exposure raw key."""

    model_config = ConfigDict(frozen=True)

    key_id: UUID
    name: str
    key_prefix: str
    raw_key: str
    scopes: list[str]
    tenant_id: str
    created_at: datetime.datetime
    expires_at: datetime.datetime | None


class APIKeyInfoResponse(BaseModel):
    """Public key metadata (raw secret is never exposed)."""

    model_config = ConfigDict(frozen=True)

    key_id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime.datetime
    last_used_at: datetime.datetime | None
    expires_at: datetime.datetime | None
