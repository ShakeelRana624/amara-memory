"""Memory routing and persistence dispatch engine for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from uuid import UUID, uuid4

from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus, RelationType
from amara.intelligence.types import IngestionCandidate
from amara.models.relationship import MemoryRelationship


class MemoryRouter:
    """Dispatches validated candidates to storage repositories and associative graph links."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    async def route_and_persist(
        self, candidate: IngestionCandidate
    ) -> tuple[bool, UUID | None, Sequence[UUID]]:
        """Route candidate record to repository or working context.

        Returns:
            Tuple of (persisted_as_new, target_record_id, created_relationship_ids).
        """
        rec = candidate.record
        dedup = candidate.deduplication_result
        now = datetime.datetime.now(datetime.UTC)
        created_rel_ids: list[UUID] = []

        # 1. Handle Deduplication Action
        if (
            dedup
            and dedup.is_duplicate
            and dedup.duplicate_memory_id
            and dedup.action_taken == "reinforce_existing"
        ):
            # Reinforce existing memory access and utility score
            await self.repository.update_metrics(
                tenant_id=rec.tenant_id,
                memory_id=dedup.duplicate_memory_id,
                utility_delta=0.5,
                accessed_at=now,
            )
            return False, dedup.duplicate_memory_id, ()

        # 2. Persist New Candidate Record
        await self.repository.create_memory(rec)

        # 3. Handle Contradictions & Relational Association Links
        for contra in candidate.contradictions:
            # Create a CONTRADICTS graph relationship linking the conflicting records
            rel_id = uuid4()
            rel = MemoryRelationship(
                relationship_id=rel_id,
                tenant_id=rec.tenant_id,
                source_id=rec.id,
                target_id=contra.existing_memory_id,
                relation_type=RelationType.CONTRADICTS,
                weight=1.0,
                bidirectional=True,
                metadata={
                    "severity": contra.severity,
                    "temporal_relationship": contra.temporal_relationship,
                    "status": contra.status,
                    "rationale": contra.resolution_rationale,
                },
            )
            await self.repository.create_relationship(rel)
            created_rel_ids.append(rel_id)

            # If the contradiction establishes clear temporal evolution, mark existing as SUPERSEDED
            if contra.status == "superseded":
                await self.repository.update_status(
                    tenant_id=rec.tenant_id,
                    memory_id=contra.existing_memory_id,
                    status=LifecycleStatus.SUPERSEDED,
                )

        return True, rec.id, tuple(created_rel_ids)
