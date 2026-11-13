"""Tests for domain-specific exceptions in AMARA."""

from __future__ import annotations

from uuid import uuid4

import pytest

from amara.exceptions import (
    AmaraError,
    CognitiveMemoryError,
    ConfigurationError,
    DuplicateMemoryError,
    InvalidMemoryStateError,
    MemoryNotFoundError,
    MemoryValidationError,
    RepositoryError,
    StorageCapacityExceededError,
    StorageConnectionError,
    StorageError,
    TenantIsolationError,
)


def test_exception_hierarchy() -> None:
    """Verify inheritance tree of AMARA exceptions."""
    assert issubclass(CognitiveMemoryError, AmaraError)
    assert issubclass(MemoryNotFoundError, CognitiveMemoryError)
    assert issubclass(DuplicateMemoryError, CognitiveMemoryError)
    assert issubclass(InvalidMemoryStateError, CognitiveMemoryError)
    assert issubclass(MemoryValidationError, CognitiveMemoryError)
    assert issubclass(TenantIsolationError, CognitiveMemoryError)
    assert issubclass(StorageError, AmaraError)
    assert issubclass(StorageConnectionError, StorageError)
    assert issubclass(StorageCapacityExceededError, StorageError)
    assert issubclass(RepositoryError, StorageError)
    assert issubclass(ConfigurationError, AmaraError)


def test_memory_not_found_error_formatting() -> None:
    """Test MemoryNotFoundError message construction."""
    mem_id = uuid4()
    err_simple = MemoryNotFoundError(mem_id)
    assert str(mem_id) in str(err_simple)
    assert err_simple.tenant_id is None

    err_tenant = MemoryNotFoundError(mem_id, tenant_id="tenant_123")
    assert "in tenant 'tenant_123'" in str(err_tenant)
    assert err_tenant.tenant_id == "tenant_123"


def test_duplicate_memory_error_formatting() -> None:
    """Test DuplicateMemoryError message construction."""
    mem_id = uuid4()
    err_simple = DuplicateMemoryError(mem_id)
    assert "already exists" in str(err_simple)

    err_tenant = DuplicateMemoryError(mem_id, tenant_id="tenant_abc")
    assert "in tenant 'tenant_abc'" in str(err_tenant)


def test_invalid_memory_state_error_formatting() -> None:
    """Test InvalidMemoryStateError message construction."""
    err = InvalidMemoryStateError("tombstoned", "active", reason="cannot resurrect purged node")
    assert "Illegal transition from state 'tombstoned' to 'active'" in str(err)
    assert "cannot resurrect purged node" in str(err)


def test_memory_validation_error_formatting() -> None:
    """Test MemoryValidationError attributes."""
    err = MemoryValidationError("confidence", "must be <= 1.0", value=1.5)
    assert err.field_name == "confidence"
    assert err.value == 1.5
    assert "Validation failed for 'confidence'" in str(err)


def test_tenant_isolation_error_formatting() -> None:
    """Test TenantIsolationError message."""
    err = TenantIsolationError(requested_tenant="corp_a", target_tenant="corp_b")
    assert "Cross-tenant access prohibited" in str(err)
    assert "corp_a" in str(err)
    assert "corp_b" in str(err)


def test_storage_capacity_exceeded_error_formatting() -> None:
    """Test StorageCapacityExceededError message."""
    err = StorageCapacityExceededError(current_count=1000, max_capacity=1000)
    assert err.current_count == 1000
    assert err.max_capacity == 1000
    assert "Storage capacity exceeded" in str(err)


def test_raising_and_catching_amara_error() -> None:
    """Verify that all domain exceptions are catchable as AmaraError."""
    with pytest.raises(AmaraError):
        raise StorageConnectionError("Failed to connect to database host.")

    with pytest.raises(AmaraError):
        raise ConfigurationError("Bad config parameter.")

    with pytest.raises(AmaraError):
        raise RepositoryError("Query timeout.")
