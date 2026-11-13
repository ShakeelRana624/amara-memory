"""Domain events emitted during memory lifecycle operations."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from amara.enums import MemoryEventType
from amara.models.temporal import validate_utc


class MemoryEvent(BaseModel):
    """Domain event representing a state or lifecycle change to a memory record."""

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1, description="Tenant scope.")
    namespace: str = Field(default="default", min_length=1, description="Namespace scope.")
    memory_id: UUID = Field(description="Target memory record identifier.")
    event_type: MemoryEventType = Field(description="Lifecycle event type.")
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Event emission timestamp in UTC.",
    )
    payload: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Structured event payload (e.g. delta changes, diagnostics).",
    )

    @field_validator("timestamp")
    @classmethod
    def _val_timestamp(cls, v: datetime.datetime) -> datetime.datetime:
        validate_utc(v, "timestamp")
        return v

    @field_validator("tenant_id", "namespace")
    @classmethod
    def _val_string_fields(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("Field cannot be empty or whitespace.")
        return v_clean
