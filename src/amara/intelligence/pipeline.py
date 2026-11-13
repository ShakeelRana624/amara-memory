"""Unified memory ingestion and intelligence pipeline for AMARA."""

from __future__ import annotations

import datetime
import logging
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from amara.contracts.repository import MemoryRepository
from amara.enums import MemoryCategory, ProvenanceSourceType
from amara.exceptions import ProviderError
from amara.intelligence.candidate_generator import MemoryCandidateGenerator
from amara.intelligence.contradiction import ContradictionDetector
from amara.intelligence.deduplication import DeduplicationEngine
from amara.intelligence.normalizer import InputNormalizer
from amara.intelligence.provenance import ProvenanceLinker
from amara.intelligence.providers.base import (
    EmbeddingProviderProtocol,
    LLMExtractionProviderProtocol,
)
from amara.intelligence.providers.rule_based import (
    DeterministicRuleEmbeddingProvider,
    RuleBasedIntelligenceProvider,
)
from amara.intelligence.router import MemoryRouter
from amara.intelligence.types import (
    ExtractedEntity,
    ExtractedFact,
    ExtractedSkill,
    IngestionCandidate,
    IngestionResult,
)
from amara.models.record import MemoryRecord

logger = logging.getLogger("amara.intelligence.pipeline")


class MemoryIngestionPipeline:
    """Coordinates input normalization, extraction, scoring, deduplication, and persistence."""

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_provider: EmbeddingProviderProtocol | None = None,
        intelligence_provider: LLMExtractionProviderProtocol | None = None,
        deduplication_threshold: float = 0.95,
        enable_fallback_on_provider_error: bool = True,
    ) -> None:
        self.repository = repository
        self.embedding_provider = embedding_provider or DeterministicRuleEmbeddingProvider()
        self.intelligence_provider = intelligence_provider or RuleBasedIntelligenceProvider()
        self.enable_fallback = enable_fallback_on_provider_error

        # Rule-based fallback provider for resilience
        self._fallback_provider = RuleBasedIntelligenceProvider()

        # Engine services
        self.candidate_generator = MemoryCandidateGenerator()
        self.deduplication_engine = DeduplicationEngine(
            repository=repository,
            similarity_threshold=deduplication_threshold,
        )
        self.contradiction_detector = ContradictionDetector(repository=repository)
        self.router = MemoryRouter(repository=repository)

    async def ingest_text(
        self,
        content: str,
        tenant_id: str,
        source_id: str,
        author_id: str,
        source_type: ProvenanceSourceType = ProvenanceSourceType.USER_INPUT,
        namespace: str = "default",
        session_id: str | None = None,
        source_event_id: str | None = None,
        explicit_category: MemoryCategory | None = None,
        asserted_at: datetime.datetime | None = None,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        parent_ids: Sequence[UUID] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> IngestionResult:
        """Ingest, extract, score, deduplicate, check conflicts, and persist cognitive memory."""
        # 1. Input normalization and validation
        normalized = InputNormalizer.validate_and_normalize(content)

        # 2. Build Provenance Source Record
        source = ProvenanceLinker.create_source(
            content=normalized,
            source_id=source_id,
            source_type=source_type,
            author_id=author_id,
            session_id=session_id,
            source_event_id=source_event_id,
            extractor_signature=self.intelligence_provider.__class__.__name__,
            metadata=metadata,
        )

        # 3. Knowledge Extraction (Facts, Entities, Skills) with Graceful Fallback
        facts: Sequence[ExtractedFact] = ()
        entities: Sequence[ExtractedEntity] = ()
        skills: Sequence[ExtractedSkill] = ()

        try:
            facts, entities, skills = await self.intelligence_provider.extract_all(normalized)
        except ProviderError as exc:
            if not self.enable_fallback:
                raise
            logger.warning(
                "Primary provider '%s' failed: %s. Falling back to rule-based extraction.",
                self.intelligence_provider.__class__.__name__,
                exc,
            )
            facts, entities, skills = await self._fallback_provider.extract_all(normalized)
        except Exception as exc:
            if not self.enable_fallback:
                raise ProviderError(
                    "intelligence_provider", f"Unexpected extraction failure: {exc}"
                ) from exc
            logger.warning("Extraction error: %s. Falling back to rule-based extraction.", exc)
            facts, entities, skills = await self._fallback_provider.extract_all(normalized)

        # 4. Dense Vector Embedding Generation
        embedding = await self.embedding_provider.embed_text(normalized)

        # 5. Candidate Generation & Structuring
        candidate = self.candidate_generator.generate_candidate(
            normalized_content=normalized,
            original_content=content,
            tenant_id=tenant_id,
            source=source,
            namespace=namespace,
            facts=facts,
            entities=entities,
            skills=skills,
            embedding=embedding,
            embedding_model_id=self.embedding_provider.model_id,
            explicit_category=explicit_category,
            asserted_at=asserted_at,
            valid_from=valid_from,
            valid_to=valid_to,
            parent_ids=parent_ids,
            custom_metadata=metadata,
        )

        # 6. Deduplication Check
        dedup_result = await self.deduplication_engine.check_duplicate(candidate)
        candidate = IngestionCandidate(
            record=candidate.record,
            source_input=candidate.source_input,
            facts=candidate.facts,
            entities=candidate.entities,
            deduplication_result=dedup_result,
        )

        # 7. Contradiction Detection
        contradictions = await self.contradiction_detector.detect_contradictions(candidate)
        candidate = IngestionCandidate(
            record=candidate.record,
            source_input=candidate.source_input,
            facts=candidate.facts,
            entities=candidate.entities,
            deduplication_result=dedup_result,
            contradictions=tuple(contradictions),
        )

        # 8. Routing & Persistence Dispatch
        is_new, target_id, created_rels = await self.router.route_and_persist(candidate)

        stored_records: tuple[MemoryRecord, ...] = ()
        reinforced_ids: tuple[UUID, ...] = ()
        dedup_count = 0

        if is_new:
            stored_records = (candidate.record,)
        elif target_id:
            reinforced_ids = (target_id,)
            dedup_count = 1

        return IngestionResult(
            stored_records=stored_records,
            reinforced_records=reinforced_ids,
            deduplicated_count=dedup_count,
            contradictions_detected=tuple(contradictions),
            created_relationships=tuple(created_rels),
        )
