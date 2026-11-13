"""AMARA Core Contracts and Abstract Interfaces.

Defines repository, event publishing, and provider adapter protocols.
"""

from __future__ import annotations

from amara.contracts.event_bus import MemoryEventHandler, MemoryEventPublisher
from amara.contracts.providers import EmbeddingAdapterProtocol, ExtractionAdapterProtocol
from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository

__all__ = [
    "EmbeddingAdapterProtocol",
    "ExtractionAdapterProtocol",
    "MemoryEventHandler",
    "MemoryEventPublisher",
    "MemoryRepository",
    "QueryFilter",
    "QuerySpec",
]
