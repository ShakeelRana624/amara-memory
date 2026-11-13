"""Base protocol defining candidate retriever implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from amara.contracts.query import QueryFilter
from amara.retrieval.types import NormalizedQuery, ScoredMemoryCandidate


@runtime_checkable
class BaseRetriever(Protocol):
    """Protocol for specialized candidate retrieval strategies."""

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Generate scored memory candidates matching the normalized query."""
        ...
