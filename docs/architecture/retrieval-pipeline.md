# AMARA Retrieval Pipeline: Multi-Stage Cognitive Retrieval & Context Assembly

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`data-model.md`](data-model.md), [`system-design.md`](system-design.md), [`security-model.md`](security-model.md)

---

## 1. Overview and Core Philosophy

Standard vector search (k-Nearest Neighbors) fails as a cognitive memory retrieval mechanism because it measures only topic similarity. A query such as *"What is the user's current project?"* will return past projects, rejected proposals, and current initiatives with nearly identical cosine distances.

AMARA implements a **5-stage cognitive retrieval pipeline** that harmonizes dense vector semantics, lexical precision, temporal interval filtering, associative graph hops, cognitive decay, and contradiction suppression into a bounded context package.

---

## 2. Pipeline Architecture Flowchart

```text
                               +----------------------------+
                               |     Client Query (q)       |
                               |    + Reference Time (t_q)  |
                               +--------------+-------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------------+
| Stage 1: Query Analysis & Decomposition                                                       |
|  - Extract target modalities (Working, Episodic, Semantic, Procedural)                        |
|  - Parse temporal reference window [t_query_start, t_query_end]                               |
|  - Generate dense query embedding vector v_q                                                  |
+-----------------------------------------------------------------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------------+
| Stage 2: Hybrid Candidate Generation                                                          |
|  +---------------------------+  +---------------------------+  +----------------------------+ |
|  |    Dense Vector Search    |  |   Full-Text BM25 Search   |  |     Graph Associative      | |
|  |     (pgvector HNSW)       |  |   (PostgreSQL tsvector)   |  |   Expansion (Edges Hop)    | |
|  +-------------+-------------+  +-------------+-------------+  +--------------+-------------+ |
|                |                              |                               |               |
|                +------------------------------+-------------------------------+               |
|                                               |                                               |
|                                               v                                               |
|                              Reciprocal Rank Fusion (RRF) Pool                                |
+-----------------------------------------------------------------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------------+
| Stage 3: Multi-Factor Cognitive Scoring & Temporal Filtering                                  |
|  - Bitemporal Interval Gating: Discard records where t_q not in [valid_from, valid_to]        |
|  - Cognitive Activation: ACT-R base-level recency decay + Salience + Utility reinforcement   |
|  - Composite Score: S(m, q) = w_rel*S_rel + w_rec*S_rec + w_sal*S_sal + w_util*S_util          |
+-----------------------------------------------------------------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------------+
| Stage 4: Contradiction Invalidation & Belief Reconciliation                                   |
|  - Detect superseded facts along ContradictionRelation edges                                  |
|  - Suppress older invalidated records in favor of active descendants                          |
+-----------------------------------------------------------------------------------------------+
                                              |
                                              v
+-----------------------------------------------------------------------------------------------+
| Stage 5: Context Assembly & Working Memory Token Budgeting                                    |
|  - Check Abstention Threshold: If max(Score) < Theta_abstain -> Return empty / flag abstention|
|  - Knapsack Token Optimization: Pack top scoring items within target token budget             |
|  - Emit structured citation block with provenance back-links                                  |
+-----------------------------------------------------------------------------------------------+
                                              |
                                              v
                               +----------------------------+
                               | Packed Context Buffer for  |
                               | Working Memory Injection   |
                               +----------------------------+
```

---

## 3. Detailed Stage Specifications

### Stage 1: Query Analysis & Decomposition
1. **Temporal Scope Extraction**: Evaluates whether the query contains relative or explicit temporal markers (e.g., "currently", "last month", "in 2024"). Determines the reference timestamp $t_q$ (defaults to current UTC time if unspecified).
2. **Modality Targeting**:
   - If the agent is executing an action, prioritizes `PROCEDURAL` memory.
   - If the query asks for biographical or interaction history, targets `EPISODIC`.
   - If asking for factual attributes, targets `SEMANTIC`.
3. **Query Vectorization**: Generates $\vec{v}_q \in \mathbb{R}^d$ via the configured `EmbeddingProvider`.

---

### Stage 2: Hybrid Candidate Generation
AMARA queries candidate records in parallel across three channels:
1. **Dense Semantic Retrieval**:
   Retrieves top $K_{dense} = 50$ records via cosine similarity:
   $$\text{Sim}_{dense}(m, q) = \frac{\vec{v}_m \cdot \vec{v}_q}{\|\vec{v}_m\| \|\vec{v}_q\|}$$
2. **Lexical Full-Text Retrieval**:
   Retrieves top $K_{lexical} = 50$ records using PostgreSQL `tsvector` with BM25-equivalent ranking.
3. **Associative Graph Expansion**:
   For any top candidate record with high initial similarity, traverses active `memory_associations` edges to retrieve adjacent concept or skill records.
4. **Reciprocal Rank Fusion (RRF)**:
   Merges candidate rankings into a unified candidate pool:
   $$\text{RRF}(m) = \sum_{c \in \{\text{dense}, \text{lexical}, \text{graph}\}} \frac{1}{60 + \text{Rank}_c(m)}$$

---

### Stage 3: Multi-Factor Cognitive Scoring Function

Candidates that survive Stage 2 undergo precise multi-factor scoring:

#### 1. Temporal Interval Gating
Records are strictly evaluated against the reference timestamp $t_q$:
$$\text{Gate}_{temporal}(m, t_q) = 
\begin{cases} 
1.0 & \text{if } m.valid\_from \le t_q < (m.valid\_to \text{ or } +\infty) \\
0.0 & \text{otherwise (unless query specifically requests historical timeline)}
\end{cases}$$

#### 2. Recency Scoring (ACT-R Power-Law Activation)
Elapsed time $\Delta t = t_q - m.last\_accessed\_at$ is penalized logarithmically:
$$S_{recency}(m) = \frac{1}{1 + \ln(1 + \frac{\Delta t}{\tau_0})}$$
where $\tau_0 = 3600 \text{ seconds}$ (1 hour base unit).

#### 3. Utility Reinforcement
Historical task utility $U(m) \in (-\infty, +\infty)$ is normalized via hyperbolic tangent:
$$S_{utility}(m) = \frac{\tanh(U(m)) + 1}{2} \in [0, 1]$$

#### 4. Composite Formula
$$\text{Score}(m, q) = \text{Gate}_{temporal}(m, t_q) \times \left[ w_{rel} \cdot S_{rel}(m, q) + w_{rec} \cdot S_{rec}(m) + w_{sal} \cdot m.salience + w_{util} \cdot S_{utility}(m) \right]$$

Default configuration weights:
- $w_{rel} = 0.50$ (Relevance)
- $w_{rec} = 0.20$ (Recency)
- $w_{sal} = 0.15$ (Intrinsic Salience)
- $w_{util} = 0.15$ (Reinforced Utility)

---

### Stage 4: Contradiction Filtering & Belief Reconciliation

1. **Superseded Invalidation**:
   If candidate record $m_A$ has an outgoing `Contradicts` relation pointing to candidate record $m_B$ and $t_{asserted}(m_A) > t_{asserted}(m_B)$:
   - Record $m_B$ is suppressed from the candidate pool.
2. **Mutual Exclusion Conflict Resolution**:
   If two candidate records assert conflicting values for the same semantic entity and attribute without an explicit superseding edge:
   - The record with the higher $\text{Score}(m, q) \times m.confidence$ is retained.
   - The conflicting record is demoted to prevent ambiguous LLM context blending.

---

### Stage 5: Context Assembly & Working Memory Budgeting

1. **Abstention Gating**:
   If $\max_{m \in \text{Pool}} \text{Score}(m, q) < \theta_{abstain}$ (default: 0.35):
   - The pipeline returns an empty context payload flagged with `abstention_recommended = True`. This signals the reasoning agent that the memory store lacks grounded knowledge, directly preventing hallucination.
2. **Knapsack Token Packing**:
   Given a target working memory token budget $B_{tokens}$ (e.g. 2,048 tokens):
   - Records are sorted by descending $\text{Score}(m, q)$.
   - Packed greedily into the context buffer until $B_{tokens}$ is exhausted.
3. **Structured Citation Generation**:
   Each injected memory block is formatted with explicit provenance citations:
   ```markdown
   [MEMORY REF #1 | Modality: SEMANTIC | Confidence: 0.95 | Source: User Dialogue]
   Content: User preferred language for code generation is Python 3.12 with strict typing.
   (Asserted: 2026-03-10 UTC | Memory ID: 7c9e6679-7425-40de-944b-e07fc1f90ae7)
   ```

