"""AMARA persistence engines and storage backends."""

from __future__ import annotations

from amara.storage.database import DatabaseManager
from amara.storage.memory import InMemoryMemoryRepository
from amara.storage.postgres import PostgresMemoryRepository
from amara.storage.schema import (
    Base,
    MemoryEventORM,
    MemoryRecordORM,
    MemoryRelationshipORM,
    MemoryVersionHistoryORM,
)
from amara.storage.vector_math import cosine_similarity, euclidean_distance

__all__ = [
    "Base",
    "DatabaseManager",
    "InMemoryMemoryRepository",
    "MemoryEventORM",
    "MemoryRecordORM",
    "MemoryRelationshipORM",
    "MemoryVersionHistoryORM",
    "PostgresMemoryRepository",
    "cosine_similarity",
    "euclidean_distance",
]
