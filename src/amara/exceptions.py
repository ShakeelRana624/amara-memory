"""Domain-specific exception hierarchy for AMARA.

All exceptions inherit from AmaraError to ensure clean error handling
and predictable failure modes across applications. Note that built-in
MemoryError is never shadowed.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID


class AmaraError(Exception):
    """Base exception for all AMARA errors."""


class ConfigurationError(AmaraError):
    """Raised when configuration validation or environment loading fails."""


class CognitiveMemoryError(AmaraError):
    """Base exception for errors originating within cognitive memory operations."""


class MemoryNotFoundError(CognitiveMemoryError):
    """Raised when a requested memory record or entity cannot be found."""

    def __init__(self, memory_id: UUID | str, tenant_id: str | None = None) -> None:
        self.memory_id = str(memory_id)
        self.tenant_id = tenant_id
        msg = f"Memory record with ID '{self.memory_id}' not found"
        if tenant_id:
            msg += f" in tenant '{tenant_id}'"
        super().__init__(f"{msg}.")


class DuplicateMemoryError(CognitiveMemoryError):
    """Raised when attempting to insert a memory record with an existing ID."""

    def __init__(self, memory_id: UUID | str, tenant_id: str | None = None) -> None:
        self.memory_id = str(memory_id)
        self.tenant_id = tenant_id
        msg = f"Memory record with ID '{self.memory_id}' already exists"
        if tenant_id:
            msg += f" in tenant '{tenant_id}'"
        super().__init__(f"{msg}.")


class InvalidMemoryStateError(CognitiveMemoryError):
    """Raised when an illegal lifecycle state transition is attempted."""

    def __init__(self, current_state: str, attempted_state: str, reason: str | None = None) -> None:
        self.current_state = current_state
        self.attempted_state = attempted_state
        msg = f"Illegal transition from state '{current_state}' to '{attempted_state}'"
        if reason:
            msg += f": {reason}"
        super().__init__(f"{msg}.")


class MemoryValidationError(CognitiveMemoryError):
    """Raised when domain data validation rules are violated."""

    def __init__(self, field_name: str, message: str, value: Any = None) -> None:
        self.field_name = field_name
        self.value = value
        super().__init__(f"Validation failed for '{field_name}': {message}")


class TenantIsolationError(CognitiveMemoryError):
    """Raised when cross-tenant data access or tenant ID mismatch is detected."""

    def __init__(self, requested_tenant: str, target_tenant: str) -> None:
        self.requested_tenant = requested_tenant
        self.target_tenant = target_tenant
        super().__init__(
            f"Cross-tenant access prohibited: requested tenant '{requested_tenant}' "
            f"does not match record tenant '{target_tenant}'."
        )


class StorageError(AmaraError):
    """Base exception for storage backend operations."""


class StorageConnectionError(StorageError):
    """Raised when connection to a storage provider fails or is lost."""


class StorageCapacityExceededError(StorageError):
    """Raised when a bounded memory store exceeds its configured capacity."""

    def __init__(self, current_count: int, max_capacity: int, message: str | None = None) -> None:
        self.current_count = current_count
        self.max_capacity = max_capacity
        detail = f"current count {current_count} reached maximum {max_capacity}."
        super().__init__(message or f"Storage capacity exceeded: {detail}")


class RepositoryError(StorageError):
    """Raised when a repository query or transactional execution fails."""


class IntelligenceError(AmaraError):
    """Base exception for memory intelligence, extraction, and cognitive processing."""


class ProviderError(IntelligenceError):
    """Raised when an external model, embedding, or extraction provider fails."""

    def __init__(
        self, provider_name: str, message: str, original_error: Exception | None = None
    ) -> None:
        self.provider_name = provider_name
        self.original_error = original_error
        super().__init__(f"Provider '{provider_name}' error: {message}")


class ExtractionError(IntelligenceError):
    """Raised when fact, entity, or candidate parsing encounters invalid structure."""


class ContradictionError(IntelligenceError):
    """Raised when an unresolvable contradiction prevents memory mutation."""
