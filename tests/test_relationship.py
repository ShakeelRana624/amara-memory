"""Tests for MemoryRelationship model, graph association constraints, and validation."""

from __future__ import annotations

import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from amara.enums import RelationType
from amara.models.relationship import MemoryRelationship


def test_valid_memory_relationship() -> None:
    """Test valid MemoryRelationship creation."""
    id_a = uuid4()
    id_b = uuid4()

    rel = MemoryRelationship(
        tenant_id="tenant_alpha",
        source_id=id_a,
        target_id=id_b,
        relation_type=RelationType.CAUSAL,
        weight=0.85,
        bidirectional=False,
        metadata={"inferred_by": "causal_engine"},
    )

    assert rel.tenant_id == "tenant_alpha"
    assert rel.source_id == id_a
    assert rel.target_id == id_b
    assert rel.relation_type == RelationType.CAUSAL
    assert rel.weight == 0.85
    assert rel.created_at.tzinfo == datetime.UTC


def test_reject_self_referential_relationship() -> None:
    """A memory cannot form a relationship with itself."""
    same_id = uuid4()
    with pytest.raises(ValidationError, match="Self-referential relationships are prohibited"):
        MemoryRelationship(
            tenant_id="tenant_alpha",
            source_id=same_id,
            target_id=same_id,
            relation_type=RelationType.ASSOCIATED_WITH,
        )


def test_reject_empty_tenant_id() -> None:
    """Tenant ID cannot be empty or whitespace."""
    with pytest.raises(ValidationError):
        MemoryRelationship(
            tenant_id="",
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=RelationType.TEMPORAL_NEXT,
        )


def test_reject_invalid_weight() -> None:
    """Relationship weight must be bounded in [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        MemoryRelationship(
            tenant_id="tenant_1",
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=RelationType.DEPENDS_ON,
            weight=1.5,
        )

    with pytest.raises(ValidationError):
        MemoryRelationship(
            tenant_id="tenant_1",
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=RelationType.DEPENDS_ON,
            weight=-0.01,
        )


def test_relationship_serialization_round_trip() -> None:
    """Verify JSON serialization round trip."""
    rel = MemoryRelationship(
        tenant_id="tenant_corp",
        source_id=uuid4(),
        target_id=uuid4(),
        relation_type=RelationType.CONTRADICTS,
    )
    json_str = rel.model_dump_json()
    restored = MemoryRelationship.model_validate_json(json_str)

    assert restored == rel
