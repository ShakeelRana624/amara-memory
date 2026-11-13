# AMARA API Contracts & Protocols Specification (v0.1)

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`data-model.md`](data-model.md), [`system-design.md`](system-design.md), [`retrieval-pipeline.md`](retrieval-pipeline.md)

---

## 1. Overview and Design Principles

AMARA enforces strict static typing and complete protocol-driven separation of concerns. Core orchestration components interact exclusively through abstract Python `typing.Protocol` interfaces, ensuring:

1. **Zero Runtime Vendor Lock-In**: Storage backends, embedding generators, and LLM extraction engines are swappable without altering domain logic.
2. **Deterministic Asynchronous Interfaces**: All I/O operations are natively asynchronous (`async`/`await`), matching modern agent runtimes.
3. **Strict Type Safety**: Complete PEP 484/526/544 annotations, checked under strict `mypy` with zero implicit `Any`.

---

## 2. Query Specifications and Response Data Classes

```python
"""API Contracts and Query Specifications for AMARA."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID

from amara.models.enums import MemoryModality, MemoryState
from amara.models.record import MemoryRecord


@dataclass(frozen=True)
class QueryFilter:
    """Multi-attribute filtering criteria for memory queries."""

    tenant_id: str
    namespace: str | None = None
    modalities: Sequence[MemoryModality] | None = None
    states: Sequence[MemoryState] = (MemoryState.ACTIVE, MemoryState.DECAYING)

    # Temporal constraints
    reference_time: datetime.datetime | None = None
    valid_at: datetime.datetime | None = None
    created_after: datetime.datetime | None = None
    created_before: datetime.datetime | None = None

    # Metadata filtering
    metadata_filter: Mapping[str, Any] = field(default_factory=dict)
    author_id: str | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class QuerySpec:
    """Comprehensive retrieval query specification."""

    query_text: str
    filter: QueryFilter
    top_k: int = 10
    token_budget: int | None = None
    include_embeddings: bool = False
    expand_associations: bool = True
    max_graph_hops: int = 1
    min_confidence: float = 0.5
    min_score: float = 0.0


@dataclass(frozen=True)
class ScoredMemory:
    """A retrieved memory record augmented with pipeline scoring diagnostics."""

    record: MemoryRecord
    composite_score: float
    relevance_score: float
    recency_score: float
    salience_score: float
    utility_score: float
    citation_text: str


@dataclass(frozen=True)
class RetrievalResponse:
    """Structured response from the AMARA retrieval pipeline."""

    query: str
    memories: Sequence[ScoredMemory]
    total_token_count: int
    abstention_recommended: bool
    execution_time_ms: float
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
```

---

## 3. Abstract Core Protocols (`typing.Protocol`)

### 3.1 StorageBackend Protocol

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Abstract persistence interface for memory storage engines."""

    async def initialize(self) -> None:
        """Initialize connections, pools, and verify schema migrations."""
        ...

    async def close(self) -> None:
        """Gracefully terminate connection pools and release resources."""
        ...

    async def store(self, record: MemoryRecord) -> None:
        """Persist a single memory record transactionally."""
        ...

    async def store_batch(self, records: Sequence[MemoryRecord]) -> None:
        """Persist a sequence of memory records in an atomic transaction."""
        ...

    async def retrieve_by_id(self, tenant_id: str, memory_id: UUID) -> MemoryRecord | None:
        """Fetch a specific memory record by its primary key within tenant scope."""
        ...

    async def query(self, spec: QuerySpec) -> Sequence[MemoryRecord]:
        """Execute a structured filter and vector similarity query."""
        ...

    async def update_state(self, tenant_id: str, memory_id: UUID, new_state: MemoryState) -> None:
        """Transition a record to a new lifecycle state."""
        ...

    async def update_metrics(
        self, tenant_id: str, memory_id: UUID, utility_delta: float, accessed_at: datetime.datetime
    ) -> None:
        """Increment access count and apply utility score reinforcement."""
        ...

    async def soft_delete(self, tenant_id: str, memory_id: UUID) -> bool:
        """Mark a record as TOMBSTONED, removing it from active queries."""
        ...

    async def hard_delete_cascade(self, tenant_id: str, root_id: UUID) -> int:
        """Recursively purge a root memory and its orphaned derivation descendants."""
        ...
```

---

### 3.2 Provider Protocols (Embedding, Extraction, Reranking)

```python
@runtime_checkable
class EmbeddingProvider(Protocol):
    """Abstract interface for text embedding models."""

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality (e.g. 1536, 768)."""
        ...

    async def embed_text(self, text: str) -> Sequence[float]:
        """Generate a dense vector embedding for a single text string."""
        ...

    async def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Generate dense vector embeddings for a batch of strings."""
        ...


@dataclass(frozen=True)
class ExtractedFact:
    """An atomic declarative fact extracted from text."""

    subject: str
    predicate: str
    object: str
    confidence: float
    asserted_at: datetime.datetime | None = None


@dataclass(frozen=True)
class ContradictionReport:
    """Report assessing whether an incoming statement contradicts existing knowledge."""

    has_contradiction: bool
    conflicting_memory_id: UUID | None
    explanation: str | None
    recommended_action: str  # e.g., 'supersede', 'reject', 'coexist'


@runtime_checkable
class ExtractionProvider(Protocol):
    """Abstract interface for LLM-driven memory extraction and reflection."""

    async def extract_facts(self, text: str) -> Sequence[ExtractedFact]:
        """Extract atomic semantic knowledge triples from unstructured dialogue."""
        ...

    async def detect_contradiction(
        self, new_statement: str, existing_statements: Sequence[str]
    ) -> ContradictionReport:
        """Evaluate semantic consistency between a new assertion and existing records."""
        ...

    async def synthesize_reflection(self, episodic_traces: Sequence[str]) -> Sequence[str]:
        """Synthesize higher-level generalized insights from episodic event sequences."""
        ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Optional cross-encoder reranking provider for second-stage candidate precision."""

    async def rerank(
        self, query: str, candidate_texts: Sequence[str]
    ) -> Sequence[tuple[int, float]]:
        """Return sequence of (candidate_index, relevance_score) sorted descending."""
        ...
```

---

### 3.3 MemoryCoordinator Public Facade

```python
@runtime_checkable
class MemoryCoordinator(Protocol):
    """Unified top-level client interface for AMARA cognitive memory."""

    async def remember(
        self,
        tenant_id: str,
        content: str,
        modality: MemoryModality = MemoryModality.EPISODIC,
        namespace: str = "default",
        salience: float = 0.5,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> MemoryRecord:
        """Ingest, vectorize, and persist a new cognitive memory record."""
        ...

    async def recall(
        self,
        tenant_id: str,
        query: str,
        namespace: str | None = None,
        modalities: Sequence[MemoryModality] | None = None,
        top_k: int = 10,
        token_budget: int | None = None,
        reference_time: datetime.datetime | None = None,
    ) -> RetrievalResponse:
        """Execute the 5-stage cognitive retrieval pipeline to assemble context."""
        ...

    async def reinforce(
        self,
        tenant_id: str,
        memory_id: UUID,
        reward: float,
    ) -> None:
        """Provide positive or negative utility feedback on a retrieved memory."""
        ...

    async def consolidate(
        self,
        tenant_id: str,
        namespace: str = "default",
    ) -> int:
        """Trigger asynchronous episodic-to-semantic consolidation clustering."""
        ...

    async def forget(
        self,
        tenant_id: str,
        memory_id: UUID,
        hard_purge: bool = False,
    ) -> bool:
        """Soft-tombstone or irreversibly purge a memory and cascade derivations."""
        ...
```

---

## 4. Exception Contracts

All exceptions inherit from `amara.exceptions.AmaraError`:

```text
AmaraError
 ├── CognitiveMemoryError
 │    ├── MemoryNotFoundError (memory_id: UUID)
 │    ├── DuplicateMemoryError (memory_id: UUID)
 │    └── ContradictionResolutionError
 ├── StorageError
 │    ├── StorageConnectionError
 │    ├── StorageCapacityExceededError
 │    └── QueryExecutionError
 ├── ProviderError
 │    ├── EmbeddingGenerationError
 │    └── ExtractionParsingError
 └── SecurityError
      ├── TenantAuthorizationError
      ├── SanitizationRejectionError
      └── DeletionCascadeError
```
Every exception provides structured attributes (such as `tenant_id`, `memory_id`, and `failure_reason`) rather than generic string error messages, enabling programmatic recovery in agent loops.
