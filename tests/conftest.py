"""Shared fixtures and pytest configuration for AMARA test suite."""

from __future__ import annotations

import datetime

import pytest


@pytest.fixture
def current_utc_time() -> datetime.datetime:
    """Provide a standardized timezone-aware UTC datetime for testing."""
    return datetime.datetime.now(datetime.UTC)
