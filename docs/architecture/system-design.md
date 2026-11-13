# AMARA System Design: Cognitive Memory Architecture Specification (v0.1)

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`data-model.md`](data-model.md), [`retrieval-pipeline.md`](retrieval-pipeline.md), [`api-contracts.md`](api-contracts.md)

---

## 1. System Philosophy and Design Goals

AMARA (Adaptive Memory Architecture for Reasoning and AI) is architected to decouple cognitive memory from both raw LLM inference engines and heavy agent orchestration frameworks. It operates as an autonomous, modular cognitive memory engine providing:

1. **Model & Framework Independence**: Zero runtime dependencies on specific LLM vendors (OpenAI, Anthropic, Google), orchestration harnesses (LangGraph, AutoGen, CrewAI), or web frameworks (FastAPI).
2. **Unified Core with Specialized Projections**: A single, normalized, bitemporal record storage model projected dynamically into Working, Episodic, Semantic, and Procedural interfaces.
3. **Enterprise Storage Foundations**: PostgreSQL with `pgvector` as the primary production persistence target, backed by an in-memory reference implementation for tests and ephemeral local execution.
4. **Clean Protocol-Driven Adapters**: External dependencies (embedding generation, text extraction, reranking) operate exclusively behind abstract Python `Protocol` interfaces.
5. **Future-Proof Extension Points**: Explicit architectural hooks for hardware compute optimization (e.g. KV-cache memory coordinates) and parametric weight continual learning.

---

## 2. High-Level Component Topology

```text
+----------------------------------------------------------------------------------------------------+
|                                    Client Application Layer                                        |
|              (Autonomous Agents, Orchestrators, Cognitive Robots, Dialogue Systems)               |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                      AMARA Facade Layer                                            |
|                                     (MemoryCoordinator)                                            |
+----------------------------------------------------------------------------------------------------+
         |                            |                               |                       |
         v                            v                               v                       v
+------------------+        +------------------+            +------------------+    +------------------+
|  Working Memory  |        | Episodic Memory  |            | Semantic Memory  |    |Procedural Memory |
|     Manager      |        |     Manager      |            |     Engine       |    |     Registry     |
| (Context Budget) |        | (Temporal Logs)  |            | (Concept Graphs) |    | (Skills & Rules) |
+------------------+        +------------------+            +------------------+    +------------------+
         |                            |                               |                       |
         +----------------------------+---------------+---------------+-----------------------+
                                                      |
                                                      v
+----------------------------------------------------------------------------------------------------+
|                                  Cognitive Engine Services                                         |
|  +---------------------------+  +---------------------------+  +--------------------------------+  |
|  |     Ingestion & Parser    |  |    Retrieval & Ranking    |  |      Decay & Forgetting        |  |
|  | (Provenance, Sanitization)|  | (Hybrid Dense/BM25/Graph) |  | (ACT-R Activation / Retention) |  |
|  +---------------------------+  +---------------------------+  +--------------------------------+  |
|  +---------------------------+  +---------------------------+  +--------------------------------+  |
|  |   Belief Revision Engine  |  |    Consolidation Worker   |  |   Context Assembly & Budget    |  |
|  | (Contradiction Detection) |  |  (Episodic -> Semantic)   |  |    (Token Knapsack Packer)     |  |
|  +---------------------------+  +---------------------------+  +--------------------------------+  |
+----------------------------------------------------------------------------------------------------+
                                                      |
                                                      v
+----------------------------------------------------------------------------------------------------+
|                                     Adapter Protocol Layer                                         |
|       +----------------------------+  +----------------------------+  +--------------------+       |
|       |     EmbeddingProvider      |  |     ExtractionProvider     |  |  RerankerProvider  |       |
|       | (Text -> Vector Embedding) |  |   (Fact & Skill Parsing)   |  | (Cross-Encoder)    |       |
|       +----------------------------+  +----------------------------+  +--------------------+       |
+----------------------------------------------------------------------------------------------------+
                                                      |
                                                      v
+----------------------------------------------------------------------------------------------------+
|                                    Storage Abstraction Layer                                       |
|                                       (StorageBackend)                                             |
|        +----------------------------------------------------------------------------------+        |
|        |                          PostgreSQL + pgvector Engine                            |        |
|        |       - Normalized `memory_records` table with Row-Level Security (RLS)          |        |
|        |       - HNSW index on embeddings, GIN index on metadata & associations           |        |
|        |       - B-tree composite indexes on tenant, modality, and temporal validity      |        |
|        +----------------------------------------------------------------------------------+        |
|        |                       Thread-Safe In-Memory Reference                            |        |
|        |       - Python stdlib storage with inverted index and vector cosine search       |        |
|        +----------------------------------------------------------------------------------+        |
+----------------------------------------------------------------------------------------------------+
```

---

## 3. Subsystem Breakdown

### 3.1 Working Memory Manager
- **Role**: Maintains the active, volatile reasoning buffer for immediate agent actions.
- **Characteristics**:
  - Bound by a strict token and entry capacity (e.g., maximum 20 items or 4,000 tokens).
  - Implements priority-eviction policies (evicting lowest salience / oldest items when capacity is reached).
  - Directly feeds the active prompt context window.
  - Supports automatic checkpointing to episodic memory when an active goal completes.

### 3.2 Episodic Memory Manager
- **Role**: Records the autobiographical, time-indexed narrative of the agent's interactions and observations.
- **Characteristics**:
  - Encapsulates discrete `EpisodeRecord` objects: user inputs, agent actions, tool outputs, environment responses.
  - Enforces explicit bitemporal timestamps (`created_at`, `asserted_at`, `valid_from`, `valid_to`).
  - Maintains causal sequence links (`prev_episode_id`, `next_episode_id`, `causal_parent_id`).

### 3.3 Semantic Memory Engine
- **Role**: Manages the agent's consolidated factual knowledge of the world, users, and domain entities.
- **Characteristics**:
  - Represents concepts as `ConceptRecord` nodes and relationships as `SemanticTriple` edges (`subject`, `predicate`, `object`).
  - Decoupled from specific interaction sessions; represents invariant or slow-evolving truths.
  - Maintains explicit confidence ratings and provenance back-links to source episodes.

### 3.4 Procedural Memory Registry
- **Role**: Stores executable skills, operational workflows, tool call protocols, and error-remediation rules.
- **Characteristics**:
  - Encapsulates `ProceduralSkill` records with trigger preconditions, parameter schemas, execution step DAGs, and expected outcomes.
  - Tracks success/failure execution metrics to dynamically update procedural utility weights.

### 3.5 Associative Linker
- **Role**: Bridges disparate modalities through relational association edges (`AssociationEdge`).
- **Characteristics**:
  - Enables associative recall: Querying an episodic event can traverse association edges to surface relevant semantic entities and procedural skills without requiring separate queries.

---

## 4. Storage Architecture: PostgreSQL + pgvector Specification

PostgreSQL is selected as the initial primary persistence engine for AMARA v0.1 because it natively unifies relational schemas, JSONB document querying, full-text search (`tsvector`), and high-performance vector similarity search (`pgvector`) within a single ACID-compliant, enterprise-ready system.

### 4.1 Indexing Topology
1. **Vector Index**: Hierarchical Navigable Small World (HNSW) index on the vector embedding column using cosine distance (`vector_cosine_ops`) or inner product:
   ```sql
   CREATE INDEX idx_memory_records_embedding ON memory_records 
   USING hnsw (embedding vector_cosine_ops) 
   WITH (m = 16, ef_construction = 64);
   ```
2. **Temporal B-Tree Composite Index**:
   ```sql
   CREATE INDEX idx_memory_records_temporal ON memory_records 
   (tenant_id, modality, valid_from, valid_to, state);
   ```
3. **Metadata & Provenance GIN Index**:
   ```sql
   CREATE INDEX idx_memory_records_metadata ON memory_records 
   USING gin (metadata jsonb_path_ops);
   ```
4. **Full-Text Search Index**:
   ```sql
   CREATE INDEX idx_memory_records_tsv ON memory_records 
   USING gin (to_tsvector('english', content));
   ```

---

## 5. Clean Decoupling and Protocol Layer

AMARA rigorously separates domain logic from infrastructure providers through abstract protocols:

```python
# Conceptual Protocol Definitions (see api-contracts.md for complete typing)
from typing import Protocol, Sequence
from amara.models.record import MemoryRecord


class StorageBackend(Protocol):
    async def store(self, record: MemoryRecord) -> None: ...
    async def retrieve_by_id(self, tenant_id: str, memory_id: str) -> MemoryRecord | None: ...
    async def query(self, query_spec: QuerySpec) -> Sequence[MemoryRecord]: ...
    async def delete(self, tenant_id: str, memory_id: str, cascade: bool = True) -> int: ...


class EmbeddingProvider(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]: ...


class ExtractionProvider(Protocol):
    async def extract_semantic_facts(self, text: str) -> Sequence[FactExtraction]: ...
    async def detect_contradictions(
        self, new_fact: str, existing_facts: Sequence[str]
    ) -> ContradictionAssessment: ...
```

This guarantees that:
- Core AMARA logic never imports `openai`, `anthropic`, `google-genai`, `fastapi`, or `langchain`.
- Unit tests run in milliseconds using mock or local deterministic embedding/storage adapters.
- Developers can swap out PostgreSQL for a cloud distributed store or in-memory cache without changing domain logic.

---

## 6. Extension Points for Future Phases

While the v0.1 release focuses strictly on cognitive memory, the system architecture introduces two explicit, future-proof extension points:

### 6.1 Extension Point A: Compute and KV-Cache Memory Coordination
- **Future Scope**: Direct integration with high-performance LLM inference servers (e.g., vLLM, TensorRT-LLM, SGLang) to coordinate prefix caching and KV-cache reuse.
- **Architectural Hook**: The `WorkingMemoryManager` includes an optional `cache_coordinate` field in working context items. When compute optimization is enabled in future releases, AMARA can emit cache block hashes corresponding to stable working memory prefixes, avoiding redundant prompt prefill computation.

### 6.2 Extension Point B: Parametric Continual Learning Coordination
- **Future Scope**: Guiding model parameter fine-tuning (e.g., LoRA updates, continual pre-training) using consolidated episodic trajectories.
- **Architectural Hook**: The `ConsolidationWorker` exports a standardized `TrainingDatasetExport` format. While AMARA will not execute backpropagation or weight training itself, it will serve as the curated cognitive data pipeline feeding parameter adaptation engines.
