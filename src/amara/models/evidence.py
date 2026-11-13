"""Evidence supporting memory validity and epistemic certainty."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from amara.models.temporal import validate_utc


class MemoryEvidence(BaseModel):
    """Corroborating evidence record grounding a memory assertion."""

    model_config = ConfigDict(frozen=True)

    evidence_id: UUID = Field(default_factory=uuid4)
    source_reference: str = Field(
        min_length=1,
        description="Reference pointer to the raw source (e.g. document URI, message ID).",
    )
    raw_payload: str | None = Field(
        default=None,
        description="Exact raw excerpt, quote, or sensor data snippet.",
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Epistemic confidence score grounded by this evidence piece.",
    )
    verified: bool = Field(
        default=False,
        description="Whether this evidence has been cryptographically or humanly verified.",
    )
    recorded_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Timestamp when evidence was ingested and attached.",
    )
    metadata: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Additional structured metadata about the evidence source.",
    )

    @field_validator("recorded_at")
    @classmethod
    def _val_recorded_at(cls, v: datetime.datetime) -> datetime.datetime:
        validate_utc(v, "recorded_at")
        return v
