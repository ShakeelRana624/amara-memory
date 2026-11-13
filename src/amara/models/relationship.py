"""Relational association model between memory records in the cognitive graph."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from amara.enums import RelationType
from amara.models.temporal import validate_utc


class MemoryRelationship(BaseModel):
    """Typed directed or bidirectional relationship connecting two memory nodes."""

    model_config = ConfigDict(frozen=True)

    relationship_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1, description="Tenant scope for isolation.")
    source_id: UUID = Field(description="Origin memory record ID.")
    target_id: UUID = Field(description="Target memory record ID.")
    relation_type: RelationType = Field(description="Semantic nature of the association.")
    weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Strength or association weight."
    )
    bidirectional: bool = Field(
        default=False, description="Whether relation applies in both directions."
    )
    metadata: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary relation metadata.",
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @field_validator("created_at")
    @classmethod
    def _val_created_at(cls, v: datetime.datetime) -> datetime.datetime:
        validate_utc(v, "created_at")
        return v

    @field_validator("tenant_id")
    @classmethod
    def _val_tenant_id(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("tenant_id cannot be empty or whitespace.")
        return v_clean

    @model_validator(mode="after")
    def _validate_not_self_referential(self) -> MemoryRelationship:
        if self.source_id == self.target_id:
            raise ValueError(
                f"Self-referential relationships are prohibited (id={self.source_id})."
            )
        return self
