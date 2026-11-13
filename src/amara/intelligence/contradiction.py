"""Contradiction and cognitive belief revision detection engine for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import ClassVar

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.intelligence.types import ContradictionCandidate, IngestionCandidate
from amara.models.record import MemoryRecord


class ContradictionDetector:
    """Detects semantic and factual conflicts across entity, attribute, value, and validity."""

    # Mutually exclusive property indicators
    _SINGLE_VALUED_PREDICATES: ClassVar[set[str]] = {
        "prefers",
        "likes",
        "runs_on",
        "port",
        "theme",
        "status",
        "version",
        "primary_runtime",
        "database",
        "location",
        "is",
        "is_a",
    }

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    async def detect_contradictions(
        self, candidate: IngestionCandidate
    ) -> Sequence[ContradictionCandidate]:
        """Examine candidate against stored memories for factual contradictions.

        Compares:
        - Entity (subject)
        - Attribute (predicate)
        - Value (object)
        - Source & Author
        - Assertion timestamp
        - Temporal validity window
        - Confidence score
        """
        contradictions: list[ContradictionCandidate] = []
        rec = candidate.record

        # If candidate has no discrete facts, check text content heuristic
        facts_to_check = candidate.facts

        # Query existing memories for same tenant and namespace
        spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=rec.tenant_id,
                namespace=rec.namespace,
            ),
            query_vector=rec.embedding,
            top_k=10,
        )
        existing_records = await self.repository.query(spec)

        for existing in existing_records:
            if existing.id == rec.id:
                continue

            existing_facts_data = existing.metadata.get("facts", [])

            for f_in in facts_to_check:
                in_subj = f_in.subject.lower()
                in_pred = f_in.predicate.lower()
                in_obj = f_in.object.lower()

                for ef in existing_facts_data:
                    ex_subj = str(ef.get("subject", "")).lower()
                    ex_pred = str(ef.get("predicate", "")).lower()
                    ex_obj = str(ef.get("object", "")).lower()
                    ex_negated = bool(ef.get("is_negated", False))

                    # Must match same entity and same attribute
                    if in_subj == ex_subj and in_pred == ex_pred:
                        # 1. Negation contradiction: one affirms, one negates
                        negation_conflict = f_in.is_negated != ex_negated and in_obj == ex_obj

                        # 2. Mutually exclusive value contradiction
                        value_conflict = (
                            in_obj != ex_obj
                            and not f_in.is_negated
                            and not ex_negated
                            and any(p in in_pred for p in self._SINGLE_VALUED_PREDICATES)
                        )

                        if negation_conflict or value_conflict:
                            # 1. Temporal comparison: prefer valid_from if defined
                            t_in = rec.temporal.valid_from or rec.temporal.asserted_at
                            t_ex = existing.temporal.valid_from or existing.temporal.asserted_at
                            time_delta = (t_in - t_ex).total_seconds()

                            # 2. Temporal validity overlap
                            valid_overlap = self._check_validity_overlap(rec, existing)

                            # 3. Confidence delta
                            conf_delta = round(rec.confidence - existing.confidence, 4)

                            # 4. Source & author comparison
                            same_author = (
                                rec.source.author_id is not None
                                and rec.source.author_id == existing.source.author_id
                            )

                            # Determine severity and temporal relationship
                            if same_author and time_delta > 0 and valid_overlap:
                                temporal_rel = "supersedes"
                                severity = "temporal_evolution"
                                status = "superseded"
                                rationale = (
                                    f"Newer assertion from author '{rec.source.author_id}' "
                                    f"supersedes historical assertion from {t_ex.isoformat()}."
                                )
                            elif (not same_author or time_delta == 0) and valid_overlap:
                                temporal_rel = (
                                    "concurrent_conflict"
                                    if abs(time_delta) <= 0.001
                                    else "divergent_sources"
                                )
                                severity = "direct_conflict"
                                status = "review_required"
                                ex_src = existing.source.author_id or existing.source.source_id
                                in_src = rec.source.author_id or rec.source.source_id
                                rationale = (
                                    f"Conflicting assertions on entity '{f_in.subject}' "
                                    f"attribute '{f_in.predicate}': '{ex_obj}' (from {ex_src}) "
                                    f"vs '{in_obj}' (from {in_src}). Preserved for review."
                                )
                            else:
                                temporal_rel = "historical_divergence"
                                severity = "direct_conflict"
                                status = "unresolved"
                                rationale = (
                                    f"Conflicting values from source '{existing.source.source_id}' "
                                    f"vs '{rec.source.source_id}'. Retained for review."
                                )

                            contradictions.append(
                                ContradictionCandidate(
                                    existing_memory_id=existing.id,
                                    candidate_memory_id=rec.id,
                                    entity=f_in.subject,
                                    attribute=f_in.predicate,
                                    existing_value=ex_obj,
                                    incoming_value=in_obj,
                                    severity=severity,
                                    temporal_relationship=temporal_rel,
                                    confidence_delta=conf_delta,
                                    status=status,
                                    resolution_rationale=rationale,
                                )
                            )

        return contradictions

    @staticmethod
    def _check_validity_overlap(rec_a: MemoryRecord, rec_b: MemoryRecord) -> bool:
        """Check if temporal validity windows [valid_from, valid_to] intersect."""
        a_from = rec_a.temporal.valid_from
        a_to = rec_a.temporal.valid_to or datetime.datetime.max.replace(tzinfo=datetime.UTC)

        b_from = rec_b.temporal.valid_from
        b_to = rec_b.temporal.valid_to or datetime.datetime.max.replace(tzinfo=datetime.UTC)

        return (a_from <= b_to) and (b_from <= a_to)
