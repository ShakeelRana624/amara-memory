"""Comprehensive domain unit tests for MemoryRecord model, validation, and lifecycle transitions."""

from __future__ import annotations

import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    ProvenanceSourceType,
)
from amara.exceptions import InvalidMemoryStateError, MemoryValidationError
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord, normalize_text


def test_memory_record_creation_defaults() -> None:
    """Test standard factory creation of MemoryRecord with default attributes."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="  User prefers Python 3.12 with strict typing.  \n\n  Always use uv.  ",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="user_alice",
        confidence=0.98,
        importance=0.85,
    )

    assert record.tenant_id == "tenant_acme"
    assert record.namespace == "default"
    assert record.memory_type == MemoryCategory.SEMANTIC
    assert record.status == LifecycleStatus.ACTIVE
    assert record.is_active is True
    assert record.is_tombstoned is False
    assert record.confidence == 0.98
    assert record.importance == 0.85
    assert record.version == 1
    assert record.root_id == record.id
    assert record.parent_ids == ()
    assert record.created_at.tzinfo == datetime.UTC
    assert record.updated_at.tzinfo == datetime.UTC

    # Verify content normalization
    expected_orig = "User prefers Python 3.12 with strict typing.  \n\n  Always use uv."
    expected_norm = "User prefers Python 3.12 with strict typing.\nAlways use uv."
    assert record.original_content == expected_orig
    assert record.normalized_content == expected_norm


def test_memory_record_content_normalization_helper() -> None:
    """Test normalize_text helper directly."""
    raw = "   Line   one   with   spaces.   \n\n\n   Line    two.   \n"
    expected = "Line one with spaces.\nLine two."
    assert normalize_text(raw) == expected


def test_controlled_content_update() -> None:
    """Updating content must bump version and update timestamps."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Initial content version 1",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_1",
    )

    initial_version = record.version
    initial_updated_at = record.updated_at

    record.update_content("Updated content version 2")

    assert record.version == initial_version + 1
    assert record.original_content == "Updated content version 2"
    assert record.normalized_content == "Updated content version 2"
    assert record.updated_at >= initial_updated_at


def test_reject_empty_content_update() -> None:
    """Attempting to update content with empty or whitespace string raises error."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Initial content",
        memory_type=MemoryCategory.EPISODIC,
        author_id="agent_1",
    )

    with pytest.raises(MemoryValidationError, match="Cannot update memory to empty content"):
        record.update_content("   ")


def test_status_transition_lifecycle() -> None:
    """Test sequential valid lifecycle state transitions across independent records."""
    # Active -> Decaying
    rec1 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Transient observation 1",
        memory_type=MemoryCategory.WORKING,
        author_id="agent_1",
    )
    assert rec1.is_active is True
    rec1.update_status(LifecycleStatus.DECAYING)
    assert rec1.status == LifecycleStatus.DECAYING

    # Decaying -> Consolidated
    rec2 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Transient observation 2",
        memory_type=MemoryCategory.WORKING,
        author_id="agent_1",
    )
    rec2.status = LifecycleStatus.DECAYING
    rec2.update_status(LifecycleStatus.CONSOLIDATED)
    assert rec2.status == LifecycleStatus.CONSOLIDATED

    # Consolidated -> Archived
    rec3 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Transient observation 3",
        memory_type=MemoryCategory.WORKING,
        author_id="agent_1",
    )
    rec3.status = LifecycleStatus.CONSOLIDATED
    rec3.update_status(LifecycleStatus.ARCHIVED)
    assert rec3.status == LifecycleStatus.ARCHIVED

    # Archived -> Tombstoned
    rec4 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Transient observation 4",
        memory_type=MemoryCategory.WORKING,
        author_id="agent_1",
    )
    rec4.status = LifecycleStatus.ARCHIVED
    rec4.update_status(LifecycleStatus.TOMBSTONED)
    assert rec4.is_tombstoned is True


def test_reject_illegal_status_transitions() -> None:
    """Test that illegal transitions raise InvalidMemoryStateError."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Archived fact",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="agent_1",
    )

    # Move to TOMBSTONED
    record.soft_delete()
    assert record.is_tombstoned is True

    # Transitioning from TOMBSTONED back to ACTIVE is illegal
    with pytest.raises(InvalidMemoryStateError) as exc:
        record.update_status(LifecycleStatus.ACTIVE)
    assert "Illegal transition from state 'tombstoned' to 'active'" in str(exc.value)


def test_record_access_metrics_tracking() -> None:
    """Test recording access events and reinforcing utility score."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Procedural rule for formatting code",
        memory_type=MemoryCategory.PROCEDURAL,
        author_id="system",
    )

    assert record.access_count == 0
    assert record.utility_score == 0.0
    initial_last_access = record.last_accessed_at
    assert initial_last_access is None

    # First retrieval access
    record.record_access(utility_delta=1.5)
    assert record.access_count == 1
    assert record.utility_score == 1.5
    current_access = record.last_accessed_at
    assert current_access is not None
    assert current_access.tzinfo == datetime.UTC

    # Second retrieval access
    record.record_access(utility_delta=-0.5)
    assert record.access_count == 2
    assert record.utility_score == 1.0


def test_add_evidence_attachment() -> None:
    """Test attaching corroborating evidence to memory record."""
    record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="User has a meeting with client at 3pm",
        memory_type=MemoryCategory.EPISODIC,
        author_id="user_bob",
    )

    evidence1 = MemoryEvidence(
        source_reference="calendar_event_998",
        raw_payload="Client Sync: 3:00 PM EST",
        confidence_score=1.0,
    )
    evidence2 = MemoryEvidence(
        source_reference="email_thread_42",
        raw_payload="See you at 3pm today.",
        confidence_score=0.9,
    )

    record.add_evidence(evidence1)
    record.add_evidence(evidence2)

    assert len(record.evidence) == 2
    assert record.evidence[0].source_reference == "calendar_event_998"
    assert record.evidence[1].source_reference == "email_thread_42"


def test_lineage_and_derivation_tracking() -> None:
    """Test derivation parent-child lineage tracking."""
    parent1_id = uuid4()
    parent2_id = uuid4()

    child_record = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Consolidated user profile summary",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="consolidation_worker",
        source_type=ProvenanceSourceType.CONSOLIDATION_SYNTHESIS,
        parent_ids=[parent1_id, parent2_id],
    )

    assert child_record.parent_ids == (parent1_id, parent2_id)
    assert child_record.root_id == parent1_id


def test_validation_rejects_invalid_confidence() -> None:
    """Ensure confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        MemoryRecord.create(
            tenant_id="tenant_1",
            content="Valid content",
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user",
            confidence=1.1,
        )

    with pytest.raises(ValidationError):
        MemoryRecord.create(
            tenant_id="tenant_1",
            content="Valid content",
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user",
            confidence=-0.05,
        )


def test_validation_rejects_invalid_importance() -> None:
    """Ensure importance outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        MemoryRecord.create(
            tenant_id="tenant_1",
            content="Valid content",
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user",
            importance=-0.1,
        )


def test_validation_rejects_empty_tenant_id() -> None:
    """Ensure empty or whitespace tenant_id is rejected."""
    with pytest.raises(ValidationError):
        MemoryRecord.create(
            tenant_id="   ",
            content="Valid content",
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user",
        )


def test_validation_rejects_empty_content() -> None:
    """Ensure empty or whitespace content is rejected."""
    with pytest.raises(MemoryValidationError, match="Memory content cannot be empty"):
        MemoryRecord.create(
            tenant_id="tenant_1",
            content="   ",
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user",
        )


def test_full_json_serialization_round_trip() -> None:
    """Test complete JSON serialization and deserialization with vectors and evidence."""
    record = MemoryRecord.create(
        tenant_id="tenant_enterprise",
        namespace="agent_researcher",
        content="Quantum annealing reduces combinatorial optimization latency.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="paper_scraper",
        confidence=0.92,
        importance=0.88,
        embedding=[0.012, -0.045, 0.982, 0.114],
        embedding_model_id="text-embedding-3-small",
        metadata={"arxiv_id": "2402.12345", "field": "physics"},
        evidence=[
            MemoryEvidence(
                source_reference="arxiv:2402.12345",
                raw_payload="Experimental evaluation confirms speedup.",
                confidence_score=0.95,
            )
        ],
    )

    json_str = record.model_dump_json()
    restored = MemoryRecord.model_validate_json(json_str)

    assert restored.id == record.id
    assert restored.tenant_id == record.tenant_id
    assert restored.normalized_content == record.normalized_content
    assert restored.embedding == record.embedding
    assert restored.embedding_model_id == "text-embedding-3-small"
    assert restored.metadata["arxiv_id"] == "2402.12345"
    assert len(restored.evidence) == 1
    assert restored.evidence[0].source_reference == "arxiv:2402.12345"
    assert restored.created_at.tzinfo == datetime.UTC


def test_tenant_isolation_integrity() -> None:
    """Verify that records preserve distinct tenant identity without leakage."""
    rec_tenant_a = MemoryRecord.create(
        tenant_id="corp_a",
        content="Confidential financial report of Corp A",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="cfo_a",
    )
    rec_tenant_b = MemoryRecord.create(
        tenant_id="corp_b",
        content="Confidential financial report of Corp B",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="cfo_b",
    )

    assert rec_tenant_a.tenant_id == "corp_a"
    assert rec_tenant_b.tenant_id == "corp_b"
    assert rec_tenant_a.tenant_id != rec_tenant_b.tenant_id
