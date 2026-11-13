"""Tests for MemorySource model, hashing, and provenance attribution."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from amara.enums import ProvenanceSourceType
from amara.models.source import MemorySource


def test_valid_memory_source_create() -> None:
    """Test standard factory creation of MemorySource with computed SHA-256 hash."""
    now = datetime.datetime.now(datetime.UTC)
    source = MemorySource.create(
        source_id="msg_123",
        source_type=ProvenanceSourceType.USER_INPUT,
        author_id="user_alice",
        content="Hello AMARA, remember that my preferred language is Python.",
        session_id="session_abc",
        asserted_at=now,
        metadata={"client": "web"},
    )

    assert source.source_id == "msg_123"
    assert source.source_type == ProvenanceSourceType.USER_INPUT
    assert source.author_id == "user_alice"
    assert source.session_id == "session_abc"
    assert len(source.content_hash) == 64
    assert source.metadata["client"] == "web"


def test_deterministic_content_hash() -> None:
    """Ensure identical inputs yield identical SHA-256 hashes."""
    now = datetime.datetime(2026, 5, 1, 10, 0, tzinfo=datetime.UTC)
    hash1 = MemorySource.compute_hash("Test content", "author_1", now)
    hash2 = MemorySource.compute_hash("Test content", "author_1", now)
    hash3 = MemorySource.compute_hash("Different content", "author_1", now)

    assert hash1 == hash2
    assert hash1 != hash3


def test_reject_empty_source_id_and_author() -> None:
    """Ensure empty or whitespace-only source_id / author_id are rejected."""
    valid_hash = "a" * 64
    with pytest.raises(ValidationError):
        MemorySource(
            source_id="",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="author_1",
            content_hash=valid_hash,
        )

    with pytest.raises(ValidationError):
        MemorySource(
            source_id="src_1",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="",
            content_hash=valid_hash,
        )


def test_reject_invalid_content_hash_length() -> None:
    """Ensure content_hash must be exactly 64 hex characters."""
    with pytest.raises(ValidationError):
        MemorySource(
            source_id="src_1",
            source_type=ProvenanceSourceType.USER_INPUT,
            author_id="author_1",
            content_hash="too_short",
        )


def test_source_serialization_round_trip() -> None:
    """Verify JSON serialization round trip."""
    source = MemorySource.create(
        source_id="src_42",
        source_type=ProvenanceSourceType.AGENT_REASONING,
        author_id="agent_planner",
        content="Synthesized plan",
    )
    json_str = source.model_dump_json()
    restored = MemorySource.model_validate_json(json_str)

    assert restored == source
