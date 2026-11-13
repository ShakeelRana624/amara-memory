"""Memory candidate generation and structuring engine for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from amara.enums import LifecycleStatus, MemoryCategory
from amara.intelligence.classifier import MemoryClassifier
from amara.intelligence.provenance import ProvenanceLinker
from amara.intelligence.scoring import ScoringEngine
from amara.intelligence.types import (
    ExtractedEntity,
    ExtractedFact,
    ExtractedSkill,
    IngestionCandidate,
)
from amara.models.record import MemoryRecord
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity


class MemoryCandidateGenerator:
    """Transforms raw cognitive perceptions and extracted facts into structured MemoryRecords."""

    def __init__(
        self,
        classifier: type[MemoryClassifier] = MemoryClassifier,
        scoring: type[ScoringEngine] = ScoringEngine,
    ) -> None:
        self.classifier = classifier
        self.scoring = scoring

    def generate_candidate(
        self,
        normalized_content: str,
        original_content: str,
        tenant_id: str,
        source: MemorySource,
        namespace: str = "default",
        facts: Sequence[ExtractedFact] = (),
        entities: Sequence[ExtractedEntity] = (),
        skills: Sequence[ExtractedSkill] = (),
        embedding: Sequence[float] | None = None,
        embedding_model_id: str | None = None,
        explicit_category: MemoryCategory | None = None,
        asserted_at: datetime.datetime | None = None,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        parent_ids: Sequence[UUID] = (),
        root_id: UUID | None = None,
        custom_metadata: Mapping[str, Any] | None = None,
    ) -> IngestionCandidate:
        """Construct a validated IngestionCandidate from analyzed input."""
        now = datetime.datetime.now(datetime.UTC)
        rec_id = uuid4()

        # 1. Classify modality
        category = self.classifier.classify(
            text=normalized_content,
            facts=facts,
            skills=skills,
            explicit_category=explicit_category,
        )

        # 2. Compute cognitive quality scores
        confidence = self.scoring.compute_confidence(
            text=normalized_content,
            source_type=source.source_type,
            extracted_confidence=1.0 if not facts else max(f.confidence for f in facts),
        )
        importance = self.scoring.compute_importance(
            text=normalized_content,
            memory_type=category,
        )

        # 3. Create primary supporting evidence
        evidence_item = ProvenanceLinker.create_evidence(
            source_reference=source.source_id,
            snippet=original_content[:500],
            confidence_score=confidence,
        )

        # 4. Assemble metadata payload
        meta = dict(custom_metadata or {})
        if entities:
            meta["entities"] = [
                {"name": e.name, "type": e.entity_type, "confidence": e.confidence}
                for e in entities
            ]
        if facts:
            meta["facts"] = [
                {
                    "subject": f.subject,
                    "predicate": f.predicate,
                    "object": f.object,
                    "is_negated": f.is_negated,
                }
                for f in facts
            ]
        if skills:
            meta["skills"] = [{"skill_name": s.skill_name, "steps": list(s.steps)} for s in skills]

        # 5. Temporal Validity
        temporal = TemporalValidity(
            asserted_at=asserted_at or now,
            valid_from=valid_from or now,
            valid_to=valid_to,
        )

        # 6. Instantiate Domain MemoryRecord
        record = MemoryRecord(
            id=rec_id,
            root_id=root_id or rec_id,
            parent_ids=tuple(parent_ids),
            tenant_id=tenant_id,
            namespace=namespace,
            memory_type=category,
            status=LifecycleStatus.ACTIVE,
            original_content=original_content,
            normalized_content=normalized_content,
            source=source,
            confidence=confidence,
            importance=importance,
            temporal=temporal,
            version=1,
            embedding=embedding,
            embedding_model_id=embedding_model_id,
            metadata=meta,
            evidence=(evidence_item,),
        )

        return IngestionCandidate(
            record=record,
            source_input=original_content,
            facts=tuple(facts),
            entities=tuple(entities),
        )
