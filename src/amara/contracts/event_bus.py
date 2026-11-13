"""Event publishing and handler contracts for memory lifecycle events."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from amara.enums import MemoryEventType
from amara.models.event import MemoryEvent


@runtime_checkable
class MemoryEventHandler(Protocol):
    """Abstract interface for consuming memory domain events."""

    async def handle(self, event: MemoryEvent) -> None:
        """Process an emitted memory event."""
        ...


@runtime_checkable
class MemoryEventPublisher(Protocol):
    """Abstract interface for publishing memory lifecycle events to subscribers."""

    async def publish(self, event: MemoryEvent) -> None:
        """Publish a memory domain event asynchronously to all registered handlers."""
        ...

    def subscribe(self, event_type: MemoryEventType, handler: MemoryEventHandler) -> None:
        """Register a handler for a specific memory event type."""
        ...

    def unsubscribe(self, event_type: MemoryEventType, handler: MemoryEventHandler) -> None:
        """Unregister a previously registered handler."""
        ...
