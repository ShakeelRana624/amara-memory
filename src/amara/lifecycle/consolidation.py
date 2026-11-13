"""Memory consolidation subsystem for clustering experiences and synthesizing semantic knowledge."""

from __future__ import annotations

import datetime
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from uuid import UUID, uuid4

from amara.contracts.repository import MemoryRepository
from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    ProvenanceSourceType,
    RelationType,
)
from amara.exceptions import ConsolidationError
from amara.intelligence.contradiction import ContradictionDetector
from amara.lifecycle.types import (
    ConsolidationCandidate,
    ConsolidationPolicy,
    ConsolidationResult,
)
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.storage.vector_math import cosine_similarity


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric word tokens."""
    return set(re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower()))


def _jaccard_similarity(tokens1: set[str], tokens2: set[str]) -> float:
    """Compute Jaccard token overlap similarity."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


class MemoryConsolidator:
    """Identifies clusters of related episodic and semantic memories and consolidates them.

    Guarantees:
    - Never merges contradictory claims into a single unsupported fact.
    - Preserves all ancestor source and evidence references.
    - Maintains complete derivation lineage via parent_ids and DERIVED_FROM edges.
    - Transitions ancestor records without destroying historical records.
    """

    def __init__(
        self,
        repository: MemoryRepository,
        contradiction_detector: ContradictionDetector | None = None,
        policy: ConsolidationPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.detector = contradiction_detector or ContradictionDetector()
        self.policy = policy or ConsolidationPolicy()

    def calculate_pairwise_similarity(self, m1: MemoryRecord, m2: MemoryRecord) -> float:
        """Compute combined semantic and lexical similarity between two records."""
        tokens1 = _tokenize(m1.normalized_content)
        tokens2 = _tokenize(m2.normalized_content)
        lexical = _jaccard_similarity(tokens1, tokens2)

        if m1.embedding is not None and m2.embedding is not None:
            vec_sim = max(0.0, cosine_similarity(m1.embedding, m2.embedding))
            return 0.6 * vec_sim + 0.4 * lexical

        return lexical

    def find_consolidation_candidates(
        self,
        records: Sequence[MemoryRecord],
    ) -> list[ConsolidationCandidate]:
        """Cluster records into candidates eligible for consolidation synthesis.

        Excludes clusters that contain mutually contradictory claims.
        """
        # Filter out tombstoned, archived, or already consolidated records
        eligible = [
            r for r in records if r.status in (LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING)
        ]

        if len(eligible) < self.policy.min_cluster_size:
            return []

        # Group by tenant and namespace first
        grouped: dict[tuple[str, str], list[MemoryRecord]] = defaultdict(list)
        for r in eligible:
            grouped[(r.tenant_id, r.namespace)].append(r)

        candidates: list[ConsolidationCandidate] = []

        for (tenant_id, namespace), pool in grouped.items():
            if len(pool) < self.policy.min_cluster_size:
                continue

            # Graph-based clustering: connect pairs with similarity >= threshold
            adj: dict[UUID, set[UUID]] = {r.id: set() for r in pool}
            record_map = {r.id: r for r in pool}

            for i in range(len(pool)):
                for j in range(i + 1, len(pool)):
                    r1 = pool[i]
                    r2 = pool[j]

                    sim = self.calculate_pairwise_similarity(r1, r2)
                    if sim >= self.policy.similarity_threshold:
                        # Check contradiction gating
                        if self.policy.prevent_contradictory_merge:
                            conflict = self.detector.detect(r1, r2)
                            if conflict.is_contradiction:
                                # Skip linking contradictory records
                                continue

                        adj[r1.id].add(r2.id)
                        adj[r2.id].add(r1.id)

            # Find connected components (clusters)
            visited: set[UUID] = set()
            for r_id in adj:
                if r_id in visited:
                    continue

                cluster: list[UUID] = []
                queue = [r_id]
                visited.add(r_id)

                while queue:
                    curr = queue.pop(0)
                    cluster.append(curr)
                    for nbr in adj[curr]:
                        if nbr not in visited:
                            visited.add(nbr)
                            queue.append(nbr)

                if (
                    len(cluster) >= self.policy.min_cluster_size
                    and len(cluster) <= self.policy.max_cluster_size
                ):
                    cluster_records = [record_map[cid] for cid in cluster]

                    # Perform final cluster-wide contradiction check
                    has_conflict = False
                    if self.policy.prevent_contradictory_merge:
                        for ci in range(len(cluster_records)):
                            for cj in range(ci + 1, len(cluster_records)):
                                c1 = cluster_records[ci]
                                c2 = cluster_records[cj]
                                if self.detector.detect(c1, c2).is_contradiction:
                                    has_conflict = True
                                    break
                            if has_conflict:
                                break

                    if has_conflict:
                        continue

                    # Synthesize proposed content and calculate combined metrics
                    proposed_text = self._synthesize_cluster_content(cluster_records)
                    avg_confidence = sum(cr.confidence for cr in cluster_records) / len(
                        cluster_records
                    )
                    max_importance = max(cr.importance for cr in cluster_records)

                    source_ids = list(dict.fromkeys(cr.source.source_id for cr in cluster_records))
                    evidence_count = sum(len(cr.evidence) for cr in cluster_records)

                    candidate = ConsolidationCandidate(
                        cluster_id=f"cluster_{uuid4().hex[:12]}",
                        tenant_id=tenant_id,
                        namespace=namespace,
                        memory_ids=tuple(cluster),
                        proposed_content=proposed_text,
                        combined_confidence=float(round(avg_confidence, 4)),
                        max_importance=float(round(max_importance, 4)),
                        source_ids=tuple(source_ids),
                        evidence_count=evidence_count,
                    )
                    candidates.append(candidate)

        return candidates

    def _synthesize_cluster_content(self, records: Sequence[MemoryRecord]) -> str:
        """Synthesize a compact, coherent proposition from clustered records."""
        # Check if records are identical / near-duplicates
        first_norm = records[0].normalized_content
        is_exact = all(r.normalized_content == first_norm for r in records)
        if is_exact:
            return records[0].original_content

        # Extract unique sentences across all records preserving order
        unique_sentences: list[str] = []
        seen_sentences: set[str] = set()

        for r in records:
            # Split by period or newline
            lines = [line.strip() for line in r.normalized_content.splitlines() if line.strip()]
            for line in lines:
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
                for s in sentences:
                    s_key = s.lower().rstrip(".!?")
                    if s_key not in seen_sentences:
                        seen_sentences.add(s_key)
                        unique_sentences.append(s)

        if not unique_sentences:
            return records[0].original_content

        return " ".join(unique_sentences)

    async def consolidate_candidate(
        self,
        candidate: ConsolidationCandidate,
        records_by_id: Mapping[UUID, MemoryRecord],
    ) -> ConsolidationResult:
        """Synthesize and store a new semantic memory from a consolidation candidate.

        Updates parent records, preserves evidence, creates DERIVED_FROM relationships,
        and ensures no historical knowledge is destroyed.
        """
        parent_records = [
            records_by_id[mid] for mid in candidate.memory_ids if mid in records_by_id
        ]
        if len(parent_records) < self.policy.min_cluster_size:
            min_sz = self.policy.min_cluster_size
            raise ConsolidationError(
                f"Cannot consolidate candidate {candidate.cluster_id}: found only "
                f"{len(parent_records)} parents in records_by_id (minimum {min_sz})."
            )

        now = datetime.datetime.now(datetime.UTC)
        primary_parent = parent_records[0]

        # Gather all corroborating evidence from parent records
        combined_evidence: list[MemoryEvidence] = []
        for p in parent_records:
            combined_evidence.extend(p.evidence)

        # Determine effective root_id
        effective_root_id = primary_parent.root_id

        # Determine temporal validity window spanning all parents
        min_asserted = min(p.temporal.asserted_at for p in parent_records)
        min_valid_from = min(p.temporal.valid_from for p in parent_records)

        # Create new consolidated SEMANTIC record
        consolidated = MemoryRecord.create(
            tenant_id=candidate.tenant_id,
            namespace=candidate.namespace,
            content=candidate.proposed_content,
            memory_type=MemoryCategory.SEMANTIC,
            source_type=ProvenanceSourceType.CONSOLIDATION_SYNTHESIS,
            author_id=f"amara:consolidator:{candidate.cluster_id}",
            confidence=candidate.combined_confidence,
            importance=candidate.max_importance,
            asserted_at=min_asserted,
            valid_from=min_valid_from,
            parent_ids=tuple(p.id for p in parent_records),
            root_id=effective_root_id,
            evidence=combined_evidence,
            metadata={
                "consolidation_cluster_id": candidate.cluster_id,
                "ancestor_count": len(parent_records),
                "synthesized_at": now.isoformat(),
            },
        )

        # Persist the new consolidated memory record
        await self.repository.store(consolidated)

        # Create DERIVED_FROM association edges linking child to parents
        created_rel_ids: list[UUID] = []
        for p in parent_records:
            rel = MemoryRelationship(
                tenant_id=candidate.tenant_id,
                source_id=consolidated.id,
                target_id=p.id,
                relation_type=RelationType.DERIVED_FROM,
                weight=1.0,
                metadata={
                    "cluster_id": candidate.cluster_id,
                    "confidence": candidate.combined_confidence,
                    "created_at": now.isoformat(),
                },
            )
            await self.repository.add_relationship(rel)
            created_rel_ids.append(rel.relationship_id)

        # Optionally transition parent records to CONSOLIDATED status
        if self.policy.auto_transition_parents:
            for p in parent_records:
                if p.status in (LifecycleStatus.ACTIVE, LifecycleStatus.DECAYING):
                    p.update_status(LifecycleStatus.CONSOLIDATED, updated_at=now)
                    await self.repository.update_status(
                        tenant_id=p.tenant_id,
                        memory_id=p.id,
                        status=LifecycleStatus.CONSOLIDATED,
                    )

        return ConsolidationResult(
            consolidated_record=consolidated,
            parent_records=tuple(parent_records),
            created_relationship_ids=tuple(created_rel_ids),
        )
