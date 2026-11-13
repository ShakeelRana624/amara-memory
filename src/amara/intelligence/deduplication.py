"""Deduplication and semantic equivalence detection engine for AMARA."""

from __future__ import annotations

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.intelligence.types import DeduplicationResult, IngestionCandidate
from amara.storage.vector_math import cosine_similarity


class DeduplicationEngine:
    """Identifies exact and semantic near-duplicates against existing memory stores."""

    def __init__(
        self,
        repository: MemoryRepository,
        similarity_threshold: float = 0.95,
    ) -> None:
        self.repository = repository
        self.similarity_threshold = similarity_threshold

    async def check_duplicate(self, candidate: IngestionCandidate) -> DeduplicationResult:
        """Evaluate candidate against repository for exact, lexical, vector, and fact identity."""
        rec = candidate.record

        # 1. Query candidate neighborhood in same tenant & namespace
        spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=rec.tenant_id,
                namespace=rec.namespace,
            ),
            query_vector=rec.embedding,
            top_k=5,
        )
        existing_records = await self.repository.query(spec)

        for existing in existing_records:
            # Skip self if checking against same record
            if existing.id == rec.id:
                continue

            # Check 1: Exact Cryptographic Content Hash
            if existing.source.content_hash == rec.source.content_hash:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_memory_id=existing.id,
                    similarity_score=1.0,
                    match_type="exact_hash",
                    action_taken="reinforce_existing",
                )

            # Check 2: Exact Normalized Content
            if existing.normalized_content == rec.normalized_content:
                return DeduplicationResult(
                    is_duplicate=True,
                    duplicate_memory_id=existing.id,
                    similarity_score=1.0,
                    match_type="exact_normalized",
                    action_taken="reinforce_existing",
                )

            # Check 3: Semantic Fact Identity (same subject, predicate, object)
            existing_facts = existing.metadata.get("facts", [])
            candidate_facts = [
                {
                    "subject": f.subject.lower(),
                    "predicate": f.predicate.lower(),
                    "object": f.object.lower(),
                    "is_negated": f.is_negated,
                }
                for f in candidate.facts
            ]
            if candidate_facts and existing_facts:
                for ef in existing_facts:
                    ef_dict = {
                        "subject": str(ef.get("subject", "")).lower(),
                        "predicate": str(ef.get("predicate", "")).lower(),
                        "object": str(ef.get("object", "")).lower(),
                        "is_negated": bool(ef.get("is_negated", False)),
                    }
                    if ef_dict in candidate_facts:
                        return DeduplicationResult(
                            is_duplicate=True,
                            duplicate_memory_id=existing.id,
                            similarity_score=0.98,
                            match_type="fact_identity",
                            action_taken="reinforce_existing",
                        )

            # Check 4: Dense Vector Cosine Similarity
            if rec.embedding and existing.embedding:
                sim = cosine_similarity(rec.embedding, existing.embedding)
                if sim >= self.similarity_threshold:
                    return DeduplicationResult(
                        is_duplicate=True,
                        duplicate_memory_id=existing.id,
                        similarity_score=round(sim, 4),
                        match_type="high_vector_similarity",
                        action_taken="reinforce_existing",
                    )

        # No duplicate found
        return DeduplicationResult(
            is_duplicate=False,
            duplicate_memory_id=None,
            similarity_score=0.0,
            match_type="none",
            action_taken="create_new",
        )
