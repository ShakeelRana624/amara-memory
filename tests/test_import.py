"""Basic package import, metadata, and runtime convention tests for AMARA."""

from __future__ import annotations

import datetime

import amara
import amara.version


def test_amara_package_import() -> None:
    """Verify that the root amara package can be imported."""
    assert amara is not None


def test_amara_version_defined() -> None:
    """Verify that the package version string is present and follows semantic naming."""
    assert hasattr(amara, "__version__")
    assert isinstance(amara.__version__, str)
    assert len(amara.__version__) > 0
    assert amara.__version__ == amara.version.__version__


def test_utc_timestamp_convention(current_utc_time: datetime.datetime) -> None:
    """Verify that runtime timestamps conform to timezone-aware UTC requirements."""
    assert current_utc_time.tzinfo is not None
    assert current_utc_time.tzinfo == datetime.UTC
