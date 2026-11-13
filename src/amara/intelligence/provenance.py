"""Source attribution and evidence provenance linking engine for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from amara.enums import ProvenanceSourceType
from amara.intelligence.normalizer import InputNormalizer
from amara.models.evidence import MemoryEvidence
from amara.models.source import MemorySource


class ProvenanceLinker:
    """Builds cryptographic and contextual provenance records and corroborating evidence."""

    @classmethod
    def create_source(
        cls,
        content: str,
        source_id: str,
        source_type: ProvenanceSourceType,
        author_id: str,
        session_id: str | None = None,
        source_event_id: str | None = None,
        extractor_signature: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemorySource:
        """Construct a validated MemorySource with cryptographic content hash."""
        content_hash = InputNormalizer.compute_content_hash(content)
        return MemorySource(
            source_id=source_id,
            source_type=source_type,
            author_id=author_id,
            session_id=session_id,
            source_event_id=source_event_id,
            content_hash=content_hash,
            extractor_signature=extractor_signature,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def create_evidence(
        cls,
        source_reference: str,
        snippet: str,
        confidence_score: float = 1.0,
        verified: bool = False,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemoryEvidence:
        """Construct an empirical MemoryEvidence item tying an assertion to source excerpt."""
        return MemoryEvidence(
            evidence_id=uuid4(),
            source_reference=source_reference,
            raw_payload=snippet,
            confidence_score=max(0.0, min(1.0, confidence_score)),
            verified=verified,
            recorded_at=datetime.datetime.now(datetime.UTC),
            metadata=dict(metadata or {}),
        )
