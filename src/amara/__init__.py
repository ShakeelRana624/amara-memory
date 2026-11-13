"""AMARA: Adaptive Memory Architecture for Reasoning and AI.

An open-source, model-agnostic cognitive memory framework designed for autonomous
reasoning agents and multi-agent workflows.
"""

from __future__ import annotations

from amara.config import AmaraConfig, DecayConfig, SecurityConfig, StorageConfig
from amara.enums import (
    DerivationType,
    LifecycleStatus,
    MemoryCategory,
    MemoryEventType,
    MemoryModality,
    MemoryState,
    MemoryType,
    ProvenanceSourceType,
    RelationType,
    SalienceLevel,
)
from amara.exceptions import (
    AmaraError,
    CognitiveMemoryError,
    ConfigurationError,
    ContradictionError,
    DuplicateMemoryError,
    ExtractionError,
    IntelligenceError,
    InvalidMemoryStateError,
    MemoryNotFoundError,
    MemoryValidationError,
    ProviderError,
    RepositoryError,
    StorageCapacityExceededError,
    StorageConnectionError,
    StorageError,
    TenantIsolationError,
)
from amara.intelligence import MemoryIngestionPipeline
from amara.models.event import MemoryEvent
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord, normalize_text
from amara.models.relationship import MemoryRelationship
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity
from amara.retrieval import (
    MemoryRetrievalEngine,
    MemorySearchResult,
    RetrievalResponse,
    RetrievalStrategy,
)
from amara.version import __version__

__all__ = [
    "AmaraConfig",
    "AmaraError",
    "CognitiveMemoryError",
    "ConfigurationError",
    "ContradictionError",
    "DecayConfig",
    "DerivationType",
    "DuplicateMemoryError",
    "ExtractionError",
    "IntelligenceError",
    "InvalidMemoryStateError",
    "LifecycleStatus",
    "MemoryCategory",
    "MemoryEvent",
    "MemoryEventType",
    "MemoryEvidence",
    "MemoryIngestionPipeline",
    "MemoryModality",
    "MemoryNotFoundError",
    "MemoryRecord",
    "MemoryRelationship",
    "MemoryRetrievalEngine",
    "MemorySearchResult",
    "MemorySource",
    "MemoryState",
    "MemoryType",
    "MemoryValidationError",
    "ProvenanceSourceType",
    "ProviderError",
    "RelationType",
    "RepositoryError",
    "RetrievalResponse",
    "RetrievalStrategy",
    "SalienceLevel",
    "SecurityConfig",
    "StorageCapacityExceededError",
    "StorageConfig",
    "StorageConnectionError",
    "StorageError",
    "TemporalValidity",
    "TenantIsolationError",
    "__version__",
    "normalize_text",
]
