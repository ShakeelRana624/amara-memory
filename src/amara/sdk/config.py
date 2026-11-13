"""Public SDK configuration management for AMARA."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class MemoryConfig(BaseModel):
    """Developer configuration settings for initializing an AMARA MemoryEngine."""

    model_config = ConfigDict(frozen=True)

    storage_backend: str = Field(
        default="memory",
        description=(
            "Underlying persistence engine ('memory' for in-memory or 'postgres' for "
            "PostgreSQL 16+)."
        ),
    )
    database_url: str | None = Field(
        default=None,
        description="Async database connection URL (e.g. 'postgresql+asyncpg://user:pass@host/db').",
    )
    db_pool_size: int = Field(
        default=10,
        gt=0,
        description="Maximum persistent PostgreSQL connection pool size.",
    )
    db_max_overflow: int = Field(
        default=10,
        ge=0,
        description="Maximum transient overflow connections for PostgreSQL.",
    )
    default_tenant_id: str = Field(
        default="default",
        description="Default tenant identifier for isolation.",
    )
    default_namespace: str = Field(
        default="default",
        description="Default memory partition/namespace.",
    )
    decay_half_life_days: float = Field(
        default=30.0,
        gt=0.0,
        description="Half-life in days for exponential recency decay.",
    )
    similarity_threshold: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for duplicate clustering and consolidation.",
    )
    abstention_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Relevance threshold below which insufficient evidence is signaled.",
    )
    token_budget: int = Field(
        default=2048,
        gt=0,
        description="Default maximum token budget for reconstructed context prompts.",
    )
    system_reserved_tokens: int = Field(
        default=256,
        ge=0,
        description="Reserved tokens for system prompt headers.",
    )
    auto_archive_expired: bool = Field(
        default=True,
        description="Automatically transition temporally expired records to ARCHIVED.",
    )

    @classmethod
    def from_env(cls) -> MemoryConfig:
        """Construct MemoryConfig from environment variables."""
        db_url = os.getenv("AMARA_DATABASE_URL")
        backend = os.getenv("AMARA_STORAGE_BACKEND", "postgres" if db_url else "memory")
        tenant = os.getenv("AMARA_TENANT_ID", "default")
        ns = os.getenv("AMARA_NAMESPACE", "default")

        half_life = float(os.getenv("AMARA_DECAY_HALF_LIFE_DAYS", "30.0"))
        sim_thresh = float(os.getenv("AMARA_SIMILARITY_THRESHOLD", "0.82"))
        abstain_thresh = float(os.getenv("AMARA_ABSTENTION_THRESHOLD", "0.35"))
        budget = int(os.getenv("AMARA_TOKEN_BUDGET", "2048"))
        reserved = int(os.getenv("AMARA_SYSTEM_RESERVED_TOKENS", "256"))
        auto_archive = os.getenv("AMARA_AUTO_ARCHIVE_EXPIRED", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        return cls(
            storage_backend=backend,
            database_url=db_url,
            default_tenant_id=tenant,
            default_namespace=ns,
            decay_half_life_days=half_life,
            similarity_threshold=sim_thresh,
            abstention_threshold=abstain_thresh,
            token_budget=budget,
            system_reserved_tokens=reserved,
            auto_archive_expired=auto_archive,
        )
