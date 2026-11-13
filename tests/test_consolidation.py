"""Unit tests for AMARA memory consolidation, clustering, and contradiction-safe synthesis."""

from __future__ import annotations

import datetime

import pytest

from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    ProvenanceSourceType,
    RelationType,
)
from amara.intelligence.contradiction import ContradictionDetector
from amara.lifecycle.consolidation import MemoryConsolidator
from amara.lifecycle.types import ConsolidationPolicy
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def consolidator(repo: InMemoryMemoryRepository) -> MemoryConsolidator:
    return MemoryConsolidator(
        repository=repo,
        contradiction_detector=ContradictionDetector(repository=repo),
        policy=ConsolidationPolicy(
            similarity_threshold=0.60,
            min_cluster_size=2,
            max_cluster_size=5,
            prevent_contradictory_merge=True,
            auto_transition_parents=True,
        ),
    )


@pytest.mark.asyncio
async def test_duplicate_memory_clustering_and_synthesis(
    consolidator: MemoryConsolidator,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test discovering near-duplicate memories and synthesizing a clean consolidated record."""
    m1 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="User preferred Python 3.12 for backend services.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_1",
        confidence=0.90,
        importance=0.70,
    )
    m1.add_evidence(MemoryEvidence(source_reference="chat_1", raw_payload="I prefer Python 3.12"))

    m2 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="User preferred Python 3.12 for backend services and data workflows.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_2",
        confidence=0.96,
        importance=0.80,
    )
    m2.add_evidence(
        MemoryEvidence(
            source_reference="chat_2", raw_payload="Python 3.12 is great for our data workflows"
        )
    )

    await repo.store(m1)
    await repo.store(m2)

    candidates = consolidator.find_consolidation_candidates([m1, m2])
    assert len(candidates) == 1
    cand = candidates[0]

    assert cand.tenant_id == "tenant_acme"
    assert set(cand.memory_ids) == {m1.id, m2.id}
    assert cand.combined_confidence == pytest.approx(0.93, abs=0.01)
    assert cand.max_importance == 0.80
    assert cand.evidence_count == 2

    # Execute consolidation synthesis
    result = await consolidator.consolidate_candidate(cand, {m1.id: m1, m2.id: m2})
    consolidated = result.consolidated_record

    # Verify synthesized memory properties
    assert consolidated.memory_type == MemoryCategory.SEMANTIC
    assert consolidated.source.source_type == ProvenanceSourceType.CONSOLIDATION_SYNTHESIS
    assert set(consolidated.parent_ids) == {m1.id, m2.id}
    assert consolidated.root_id == m1.root_id
    assert len(consolidated.evidence) == 2
    assert consolidated.status == LifecycleStatus.ACTIVE

    # Verify parent records are transitioned to CONSOLIDATED without being deleted
    p1 = await repo.get_by_id("tenant_acme", m1.id)
    p2 = await repo.get_by_id("tenant_acme", m2.id)
    assert p1 is not None
    assert p1.status == LifecycleStatus.CONSOLIDATED
    assert p2 is not None
    assert p2.status == LifecycleStatus.CONSOLIDATED

    # Verify DERIVED_FROM association relationships were created in repository
    rels = await repo.get_relationships("tenant_acme", consolidated.id)
    derived_rels = [r for r in rels if r.relation_type == RelationType.DERIVED_FROM]
    assert len(derived_rels) == 2
    target_ids = {r.target_id for r in derived_rels}
    assert target_ids == {m1.id, m2.id}


@pytest.mark.asyncio
async def test_consolidation_strictly_refuses_to_merge_contradictory_facts(
    consolidator: MemoryConsolidator,
    repo: InMemoryMemoryRepository,
) -> None:
    """CRITICAL RULE: Contradictory claims must NEVER be merged into a single unsupported fact."""
    now = datetime.datetime.now(datetime.UTC)

    # Two memories with high lexical overlap but contradictory factual assertions!
    m1 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Production Redis cache is running on port 6379.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="devops",
        asserted_at=now,
    )
    m2 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Production Redis cache is not running on port 6379.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="devops",
        asserted_at=now + datetime.timedelta(seconds=1),
    )

    await repo.store(m1)
    await repo.store(m2)

    # find_consolidation_candidates must reject merging them due to contradiction gating!
    candidates = consolidator.find_consolidation_candidates([m1, m2])
    assert len(candidates) == 0, (
        "Contradictory records must not be bundled into a consolidation candidate!"
    )
