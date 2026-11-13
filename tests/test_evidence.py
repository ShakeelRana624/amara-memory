"""Tests for MemoryEvidence model and confidence bounds."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from amara.models.evidence import MemoryEvidence


def test_valid_memory_evidence() -> None:
    """Test valid MemoryEvidence creation."""
    now = datetime.datetime.now(datetime.UTC)
    evidence = MemoryEvidence(
        source_reference="doc://policies/security_2026.pdf#page=12",
        raw_payload="All passwords must be rotated every 90 days.",
        confidence_score=0.95,
        verified=True,
        recorded_at=now,
        metadata={"reviewer": "sec_audit"},
    )

    assert evidence.source_reference.startswith("doc://")
    assert evidence.confidence_score == 0.95
    assert evidence.verified is True
    assert evidence.metadata["reviewer"] == "sec_audit"


def test_reject_invalid_confidence_scores() -> None:
    """Confidence score must be strictly bounded within [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        MemoryEvidence(
            source_reference="ref_1",
            confidence_score=-0.1,
        )

    with pytest.raises(ValidationError):
        MemoryEvidence(
            source_reference="ref_1",
            confidence_score=1.05,
        )


def test_reject_naive_recorded_at() -> None:
    """Ensure naive datetimes are rejected for recorded_at."""
    naive_dt = datetime.datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(ValidationError):
        MemoryEvidence(
            source_reference="ref_1",
            recorded_at=naive_dt,
        )


def test_evidence_serialization_round_trip() -> None:
    """Verify serialization round-trip for MemoryEvidence."""
    evidence = MemoryEvidence(
        source_reference="msg_001",
        raw_payload="Raw quote excerpt",
        confidence_score=0.88,
    )
    json_str = evidence.model_dump_json()
    restored = MemoryEvidence.model_validate_json(json_str)

    assert restored == evidence
