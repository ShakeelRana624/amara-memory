# AMARA Architecture Overview

## 1. Mission and Problem Statement

**AMARA** (Adaptive Memory Architecture for Reasoning and AI) is an open-source, model-agnostic cognitive memory framework designed to provide autonomous AI agents and reasoning systems with persistent, structured, and contextually adaptive memory.

Current Large Language Model (LLM) agents suffer from critical memory limitations:
- **Stateless Execution**: Models lose state across invocation cycles.
- **Context Window Bottlenecks**: Expanding token contexts induces degradation in multi-hop reasoning, increases quadratic latency, and incurs prohibitive financial cost.
- **Naive Retrieval Failure**: Standard RAG (Retrieval-Augmented Generation) treats memory as flat text chunks, discarding temporal relationships, causal sequences, operational skills, and recency/importance decay.

AMARA models memory after cognitive architectures rather than naive text stores or hardware cache layers.

---

## 2. Core Architectural Principles

1. **Exclusively Cognitive Memory Scope**  
   AMARA focuses strictly on the semantic, episodic, working, and procedural layers of intelligence. It does *not* manage GPU memory allocation, KV-cache quantization, training-time activation checkpointing, or parametric weight updates.

2. **Strict Model Agnosticism**  
   The core framework has zero dependencies on specific LLM vendors, proprietary APIs, or heavy runtime frameworks. AMARA provides clean protocols and data structures; any reasoning engine can interact with AMARA memory representations.

3. **Multi-Tier Memory Hierarchy**  
   Cognitive memory is structured across four primary modalities:
   - **Working Memory**: Active short-term scratchpad, current task goals, ephemeral constraints, and active reasoning context.
   - **Episodic Memory**: Time-indexed, sequential records of specific experiences, agent actions, environment observations, and conversational turns.
   - **Semantic Memory**: Generalized factual knowledge, entity relationships, ontology concepts, and distilled world understanding decoupled from specific temporal occurrences.
   - **Procedural Memory**: Reusable routines, skills, tool-usage patterns, workflows, and algorithmic execution sequences.

4. **Bi-directional Memory Dynamics**  
   Memory is not static storage; it undergoes active lifecycle management:
   - *Ingestion & Association*: Indexing new percepts with cross-references to existing knowledge.
   - *Decay & Forgetting*: Ebbinghaus-inspired temporal decay, relevance discounting, and priority weighting.
   - *Consolidation & Reflection*: Periodically synthesizing episodic traces into durable semantic rules and procedural capabilities.

---

## 3. Layered System Architecture

```text
+-------------------------------------------------------------------+
|                        Client Applications                        |
|        (Autonomous Agents, Orchestrators, Chat Systems)           |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                       AMARA Core Interface                        |
|                  (MemoryCoordinator / Facade)                     |
+-------------------------------------------------------------------+
                                 |
        +------------------------+------------------------+
        |                        |                        |
        v                        v                        v
+---------------+        +---------------+        +---------------+
| Working Memory|        |Episodic Memory|        |Semantic Memory|
|    Buffer     |        |     Store     |        |   Store       |
+---------------+        +---------------+        +---------------+
        |                        |                        |
        +------------------------+------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|               Memory Operations & Cognitive Lifecycle             |
|        [Scoring & Decay] [Consolidation] [Context Assembly]       |
+-------------------------------------------------------------------+
                                 |
                                 v
+-------------------------------------------------------------------+
|                   Storage & Retrieval Adapters                    |
|             (In-Memory, SQLite, Vector, Graph, SaaS)              |
+-------------------------------------------------------------------+
```

---

## 4. Subsystems and Boundaries

### 4.1 Storage Abstraction Layer
All persistence mechanisms implement explicit Python `Protocol` interfaces. The core engine interacts solely with abstract storage protocols (e.g., `MemoryStorageRecord`, `StorageBackend`), allowing interchangeable backends:
- Local volatile in-memory (testing and ephemeral sessions)
- Embedded persistent (SQLite / local document stores)
- Scalable distributed stores (Vector indices, Graph DBs, Object stores)
- Cloud/SaaS hosted endpoint (future AMARA platform)

### 4.2 Working Memory Subsystem
Maintains bounded, highly accessible state for current execution steps. Manages context budget allocations and enforces token/entry thresholds.

### 4.3 Episodic Memory Subsystem
Encapsulates discrete event episodes with:
- Standardized UTC timestamps
- Episode boundaries and causal links
- Emotional/importance valence scores
- Temporal ordering and interval queries

### 4.4 Semantic Knowledge Subsystem
Maintains concept graphs, entity networks, and validated factual assertions. Supports associative querying and concept traversal.

### 4.5 Procedural Subsystem
Maintains structured workflows, tool definitions, successful operational trajectories, and failure correction recipes.

---

## 5. Security & Isolation

- **Tenant and Agent Segregation**: Memory namespaces are strictly enforced to prevent cross-agent or cross-user context contamination.
- **Zero Secret Ingestion**: Sanitization filters prevent inadvertent recording of sensitive API keys or credentials into persistent memory stores.

---

## 6. Path Toward SaaS Platform

While the open-source AMARA core is self-contained and operates entirely locally, its protocol-driven architecture is deliberately designed to allow seamless migration to a hosted AMARA SaaS platform:
- Storage protocols can map to gRPC / REST API cloud endpoints.
- Synchronization managers will handle offline-local to cloud replication.
- Multi-agent shared memory spaces will be managed via cloud-native access control.
