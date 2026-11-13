# AMARA Known Limitations and Operational Boundaries (v0.1)

This document provides transparent disclosure of architectural, operational, and computational boundaries in AMARA v0.1.

---

## 1. Architectural Scope Boundaries

### A. Non-Parametric Context Augmentation (No Weight Modification)
AMARA is an **external cognitive memory architecture**. It provides structured, persistent, and adaptive cognitive context to language models and autonomous agents in prompt space. AMARA:
- **Does NOT modify neural network weights** or perform gradient-based continual fine-tuning.
- **Does NOT claim parametric continual learning**.
- Operates strictly through verified external context retrieval, prompt knapsack packing, and structured citation anchors (`[REF-N]`).

### B. Embedding Generation Trade-offs
- **Deterministic Rule-Based Embeddings**: AMARA's default zero-dependency provider generates 1536-dimensional unit vectors via lexical feature hashing. While deterministic, fast (sub-millisecond), and free of API keys or GPU requirements, it captures lexical and syntactic similarity rather than deep semantic abstraction.
- **Frontier Neural Embeddings**: In production deployments where semantic paraphrasing is paramount (e.g., matching "automobile" to "vehicle"), a dense embedding model (e.g., OpenAI `text-embedding-3-small`, Hugging Face `all-MiniLM-L6-v2`) should be configured via `MemoryConfig`.

---

## 2. Storage & Scaling Boundaries

### A. Single-Node PostgreSQL Capacity
- In PostgreSQL 16 with pgvector HNSW indexing, search latency remains sub-50ms up to ~1,000,000 memory records per tenant. Beyond 1,000,000 records, database horizontal sharding or dedicated vector databases (e.g., Milvus, Pinecone, Qdrant) may be required.
- Connection pooling requires PgBouncer in transaction pooling mode (`pool_mode = transaction`) to prevent socket exhaustion when servicing hundreds of concurrent agent workers.

### B. High-Concurrency Write Contention on Identical Records
- AMARA employs Optimistic Concurrency Control (OCC) using monotonic record `version` counters.
- If multiple concurrent worker processes attempt to mutate the exact same `memory_id` simultaneously, the first write commits and subsequent writes will raise `ConcurrencyError`.
- Applications with high write contention on identical memory nodes should implement exponential backoff retries or serialize updates per record ID.

---

## 3. Retrieval & Context Reconstruction Boundaries

### A. Multi-Hop Graph Traversal Depth
- AMARA's `RelationalRetriever` supports multi-hop associative traversal across relationship edges (`DERIVED_FROM`, `CONTRADICTS`, `DEPENDS_ON`, `CAUSAL`, `ASSOCIATED_WITH`).
- In v0.1, traversal depth is optimal up to **2–3 hops**. Traversals beyond 3 hops risk exponential candidate fan-out and increased database latency.

### B. Token Budget vs. Context Completeness
- Context reconstruction enforces a strict knapsack token budget (`ContextBudget`).
- In situations with hundreds of corroborating evidence items, candidates with lower composite evidence rank scores are omitted (`candidates_omitted_budget`).
- Increasing the token budget allows more comprehensive evidence packing, but linearly increases downstream LLM inference latency and token operational expenditure.

---

## 4. Benchmark & Research Boundaries

### A. Synthetic vs. Production Dialogue Distribution
- Benchmark evaluations (LongMemEval, LoCoMo) utilize standardized synthetic and semi-synthetic dialogue datasets with controlled ground truths. Real-world user interactions often exhibit greater conversational noise, colloquial slang, and ambiguous temporal references.

### B. Contradiction Detection Heuristics
- AMARA's rule-based contradiction detector evaluates entity-attribute-value conflicts, temporal overlap, and confidence deltas. Complex philosophical, subjective, or multi-faceted contradictions without clear temporal superseding may be flagged as `review_required` rather than automatically superseded.

---

## 5. Roadmap & Future Mitigations

The following mitigations are planned for AMARA v0.2+:
1. **Hierarchical Graph Indexing**: Graph neural indexing for constant-time multi-hop relationship traversals.
2. **Distributed Storage Adapters**: Native connectors for distributed vector engines and read-replica routing.
3. **Parametric Reranker Distillation**: Lightweight local cross-encoders for microsecond reranking without LLM API overhead.

