"""Tests for MemoryEvent domain event schema and serialization."""

from __future__ import annotations

import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from amara.enums import MemoryEventType
from amara.models.event import MemoryEvent


def test_valid_memory_event() -> None:
    """Test valid MemoryEvent creation."""
    mem_id = uuid4()
    event = MemoryEvent(
        tenant_id="tenant_finance",
        namespace="ledger_agent",
        memory_id=mem_id,
        event_type=MemoryEventType.CREATED,
        payload={"initial_salience": 0.9},
    )

    assert event.tenant_id == "tenant_finance"
    assert event.namespace == "ledger_agent"
    assert event.memory_id == mem_id
    assert event.event_type == MemoryEventType.CREATED
    assert event.timestamp.tzinfo == datetime.UTC
    assert event.payload["initial_salience"] == 0.9


def test_reject_empty_event_tenant_and_namespace() -> None:
    """Ensure empty tenant or namespace triggers validation errors."""
    with pytest.raises(ValidationError):
        MemoryEvent(
            tenant_id="   ",
            namespace="default",
            memory_id=uuid4(),
            event_type=MemoryEventType.UPDATED,
        )

    with pytest.raises(ValidationError):
        MemoryEvent(
            tenant_id="tenant_1",
            namespace="",
            memory_id=uuid4(),
            event_type=MemoryEventType.UPDATED,
        )


def test_event_serialization_round_trip() -> None:
    """Verify JSON serialization and deserialization for MemoryEvent."""
    event = MemoryEvent(
        tenant_id="tenant_dev",
        memory_id=uuid4(),
        event_type=MemoryEventType.CONSOLIDATED,
        payload={"derived_concept_id": str(uuid4())},
    )

    json_str = event.model_dump_json()
    restored = MemoryEvent.model_validate_json(json_str)

    assert restored == event
