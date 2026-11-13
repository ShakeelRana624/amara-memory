"""Tests for TemporalValidity domain model and UTC timezone constraints."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from amara.models.temporal import TemporalValidity, validate_utc


def test_valid_temporal_validity() -> None:
    """Test successful construction of TemporalValidity with valid UTC datetimes."""
    now = datetime.datetime.now(datetime.UTC)
    later = now + datetime.timedelta(days=30)
    tv = TemporalValidity(asserted_at=now, valid_from=now, valid_to=later)

    assert tv.asserted_at == now
    assert tv.valid_from == now
    assert tv.valid_to == later


def test_temporal_validity_unbounded_future() -> None:
    """Test validity window unbounded in the future (valid_to is None)."""
    now = datetime.datetime.now(datetime.UTC)
    tv = TemporalValidity(asserted_at=now, valid_from=now, valid_to=None)

    assert tv.valid_to is None
    future_time = now + datetime.timedelta(days=365)
    assert tv.is_valid_at(future_time) is True


def test_temporal_validity_is_valid_at_intervals() -> None:
    """Test interval boundary checks for is_valid_at."""
    t0 = datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.UTC)
    t1 = datetime.datetime(2026, 6, 1, 0, 0, tzinfo=datetime.UTC)
    t2 = datetime.datetime(2026, 12, 31, 23, 59, tzinfo=datetime.UTC)

    tv = TemporalValidity(asserted_at=t0, valid_from=t1, valid_to=t2)

    # Before validity window
    assert tv.is_valid_at(datetime.datetime(2026, 5, 31, 23, 59, tzinfo=datetime.UTC)) is False
    # At start of validity window (inclusive)
    assert tv.is_valid_at(t1) is True
    # In middle of validity window
    assert tv.is_valid_at(datetime.datetime(2026, 8, 15, 12, 0, tzinfo=datetime.UTC)) is True
    # At end of validity window (exclusive)
    assert tv.is_valid_at(t2) is False
    # After validity window
    assert tv.is_valid_at(datetime.datetime(2027, 1, 1, 0, 0, tzinfo=datetime.UTC)) is False


def test_temporal_validity_rejects_naive_datetime() -> None:
    """Ensure naive datetimes are rejected with validation error."""
    naive_dt = datetime.datetime(2026, 1, 1, 12, 0, 0)  # No tzinfo

    with pytest.raises(ValidationError) as exc:
        TemporalValidity(asserted_at=naive_dt, valid_from=naive_dt)
    assert "must be timezone-aware and set to UTC" in str(exc.value)


def test_temporal_validity_rejects_non_utc_timezone() -> None:
    """Ensure non-UTC timezone-aware datetimes are rejected."""
    non_utc_tz = datetime.timezone(datetime.timedelta(hours=-5))
    non_utc_dt = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=non_utc_tz)

    with pytest.raises(ValidationError) as exc:
        TemporalValidity(asserted_at=non_utc_dt, valid_from=non_utc_dt)
    assert "must be timezone-aware and set to UTC" in str(exc.value)


def test_temporal_validity_rejects_inverted_interval() -> None:
    """Ensure valid_to < valid_from raises validation error."""
    now = datetime.datetime.now(datetime.UTC)
    earlier = now - datetime.timedelta(days=1)

    with pytest.raises(ValidationError) as exc:
        TemporalValidity(asserted_at=now, valid_from=now, valid_to=earlier)
    assert "cannot be before" in str(exc.value)


def test_temporal_validity_serialization_round_trip() -> None:
    """Verify JSON serialization and deserialization preserves equality."""
    now = datetime.datetime.now(datetime.UTC)
    tv = TemporalValidity(asserted_at=now, valid_from=now, valid_to=None)

    json_str = tv.model_dump_json()
    restored = TemporalValidity.model_validate_json(json_str)

    assert restored == tv
    assert restored.asserted_at.tzinfo == datetime.UTC


def test_temporal_validity_current_factory() -> None:
    """Test TemporalValidity.current factory helper."""
    tv = TemporalValidity.current()
    assert tv.valid_to is None
    assert tv.asserted_at.tzinfo == datetime.UTC
    assert tv.valid_from.tzinfo == datetime.UTC


def test_validate_utc_helper() -> None:
    """Direct tests for validate_utc utility function."""
    assert validate_utc(None) is None
    utc_dt = datetime.datetime.now(datetime.UTC)
    assert validate_utc(utc_dt) == utc_dt

    with pytest.raises(ValueError, match="must be timezone-aware"):
        validate_utc(datetime.datetime.now())
