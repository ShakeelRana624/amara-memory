"""Source attribution and provenance model for AMARA memories."""

from __future__ import annotations

import datetime
import hashlib
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from amara.enums import ProvenanceSourceType


class MemorySource(BaseModel):
    """Source attribution and origin metadata for a memory record."""

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(min_length=1, description="Identifier of the origin source.")
    source_type: ProvenanceSourceType = Field(
        description="Categorical origin type (user, agent, tool, etc.)."
    )
    author_id: str = Field(
        min_length=1, description="Author identifier (user ID, agent ID, tool name)."
    )
    session_id: str | None = Field(
        default=None, description="Optional conversation/task session ID."
    )
    source_event_id: str | None = Field(
        default=None, description="Raw message or event identifier."
    )
    content_hash: str = Field(
        min_length=64,
        max_length=64,
        description="SHA-256 hash of the content payload at ingestion for integrity.",
    )
    extractor_signature: str | None = Field(
        default=None,
        description="Identifier of model or rule signature that derived this memory.",
    )
    metadata: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Additional unstructured source metadata.",
    )

    @classmethod
    def compute_hash(
        cls,
        content: str,
        author_id: str,
        asserted_at: datetime.datetime | None = None,
    ) -> str:
        """Compute deterministic SHA-256 hash of memory content and attribution."""
        hasher = hashlib.sha256()
        hasher.update(content.encode("utf-8"))
        hasher.update(author_id.strip().encode("utf-8"))
        if asserted_at is not None:
            hasher.update(asserted_at.isoformat().encode("utf-8"))
        return hasher.hexdigest()

    @classmethod
    def create(
        cls,
        source_id: str,
        source_type: ProvenanceSourceType,
        author_id: str,
        content: str,
        session_id: str | None = None,
        source_event_id: str | None = None,
        extractor_signature: str | None = None,
        asserted_at: datetime.datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemorySource:
        """Convenience factory computing content hash automatically."""
        computed_hash = cls.compute_hash(content, author_id, asserted_at)
        return cls(
            source_id=source_id.strip(),
            source_type=source_type,
            author_id=author_id.strip(),
            session_id=session_id.strip() if session_id else None,
            source_event_id=source_event_id.strip() if source_event_id else None,
            content_hash=computed_hash,
            extractor_signature=extractor_signature.strip() if extractor_signature else None,
            metadata=dict(metadata or {}),
        )
