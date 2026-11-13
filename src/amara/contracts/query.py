"""Query specification contracts and filter parameters."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from amara.enums import LifecycleStatus, MemoryCategory


@dataclass(frozen=True)
class QueryFilter:
    """Multi-attribute filtering criteria for repository lookups."""

    tenant_id: str
    namespace: str | None = None
    memory_types: Sequence[MemoryCategory] | None = None
    statuses: Sequence[LifecycleStatus] = (
        LifecycleStatus.ACTIVE,
        LifecycleStatus.DECAYING,
    )

    # Temporal filters
    reference_time: datetime.datetime | None = None
    valid_at: datetime.datetime | None = None
    created_after: datetime.datetime | None = None
    created_before: datetime.datetime | None = None

    # Attribution & provenance filters
    author_id: str | None = None
    session_id: str | None = None
    source_id: str | None = None

    # Arbitrary metadata equality filter
    metadata_filter: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QuerySpec:
    """Comprehensive query specification combining lexical, vector, and relational constraints."""

    filter: QueryFilter
    query_text: str | None = None
    query_vector: Sequence[float] | None = None
    top_k: int = 10
    min_confidence: float = 0.0
    min_importance: float = 0.0
    include_tombstoned: bool = False
    expand_relationships: bool = False
    max_relationship_hops: int = 1
