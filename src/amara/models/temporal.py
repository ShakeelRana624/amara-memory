"""Temporal validity model for bitemporal real-world truth and event occurrence."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_utc(
    v: datetime.datetime | None, field_name: str = "datetime"
) -> datetime.datetime | None:
    """Validate that datetime is timezone-aware and set to UTC."""
    if v is not None and (v.tzinfo is None or v.tzinfo != datetime.UTC):
        raise ValueError(
            f"'{field_name}' must be timezone-aware and set to UTC (got tzinfo={v.tzinfo})."
        )
    return v


class TemporalValidity(BaseModel):
    """Bitemporal validity window modeling real-world truth and event occurrence."""

    model_config = ConfigDict(frozen=True)

    asserted_at: datetime.datetime = Field(
        description="When the event or fact occurred or was asserted in the real world."
    )
    valid_from: datetime.datetime = Field(description="Start of the temporal validity window.")
    valid_to: datetime.datetime | None = Field(
        default=None,
        description="End of temporal validity window (None represents unbounded future).",
    )

    @field_validator("asserted_at")
    @classmethod
    def _val_asserted_at(cls, v: datetime.datetime) -> datetime.datetime:
        validate_utc(v, "asserted_at")
        return v

    @field_validator("valid_from")
    @classmethod
    def _val_valid_from(cls, v: datetime.datetime) -> datetime.datetime:
        validate_utc(v, "valid_from")
        return v

    @field_validator("valid_to")
    @classmethod
    def _val_valid_to(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return validate_utc(v, "valid_to")

    @model_validator(mode="after")
    def _validate_interval_order(self) -> TemporalValidity:
        """Ensure valid_to >= valid_from when valid_to is specified."""
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError(
                f"valid_to ({self.valid_to.isoformat()}) cannot be before "
                f"valid_from ({self.valid_from.isoformat()})."
            )
        return self

    def is_valid_at(self, reference_time: datetime.datetime) -> bool:
        """Check whether this temporal window covers the given reference time."""
        validate_utc(reference_time, "reference_time")
        return self.valid_from <= reference_time and (
            self.valid_to is None or self.valid_to > reference_time
        )

    @classmethod
    def current(cls, asserted_at: datetime.datetime | None = None) -> TemporalValidity:
        """Construct a validity window starting now and unbounded into the future."""
        now = datetime.datetime.now(datetime.UTC)
        effective_asserted = asserted_at or now
        validate_utc(effective_asserted, "asserted_at")
        return cls(asserted_at=effective_asserted, valid_from=now, valid_to=None)
