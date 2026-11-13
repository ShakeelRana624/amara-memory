"""Domain-specific exception hierarchy for AMARA.

All exceptions inherit from AmaraError to ensure clean error handling
and predictable failure modes across applications. Note that built-in
MemoryError is never shadowed.
"""

from __future__ import annotations


class AmaraError(Exception):
    """Base exception for all AMARA errors."""


class CognitiveMemoryError(AmaraError):
    """Base exception for errors originating within cognitive memory operations."""


class MemoryNotFoundError(CognitiveMemoryError):
    """Raised when a requested memory record or entity cannot be found."""

    def __init__(self, memory_id: str, message: str | None = None) -> None:
        self.memory_id = memory_id
        super().__init__(message or f"Memory record with ID '{memory_id}' not found.")


class DuplicateMemoryError(CognitiveMemoryError):
    """Raised when attempting to insert a memory record with an existing ID."""

    def __init__(self, memory_id: str, message: str | None = None) -> None:
        self.memory_id = memory_id
        super().__init__(message or f"Memory record with ID '{memory_id}' already exists.")


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


class RetrievalError(AmaraError):
    """Raised when memory retrieval, ranking, or indexing operations fail."""
