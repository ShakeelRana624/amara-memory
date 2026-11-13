# AMARA Research Questions: Hypotheses, Formulations, and Empirical Verification

**Author**: AMARA Architecture & AI Research Team  
**Date**: November 2026  
**Status**: Specification Baseline (v0.1)  
**Related Documents**: [`literature-review.md`](literature-review.md), [`research-gaps.md`](research-gaps.md)

---

## 1. Overview and Scientific Framework

The development of AMARA is guided by a formal empirical research agenda designed to resolve the fundamental gaps identified in contemporary agent memory architectures. Rather than relying on speculative claims of novelty, every architectural feature in AMARA corresponds to a specific, testable Research Question (RQ) with articulated null and alternative hypotheses, mathematical models, and standardized benchmark evaluation methodologies.

---

## 2. Research Questions and Formal Hypotheses

### Research Question 1 (RQ1): Unified Schema Polymorphism vs. Fragmented Specialized Stores

> **Question**: *Can a unified, strongly-typed memory record schema efficiently project across distinct working, episodic, semantic, and procedural indices without incurring prohibitive storage overhead or query latency compared to isolated specialized databases?*

- **Hypothesis $H_0$**: A unified polymorphic schema introduces redundant indexing overhead and increased query latency ($>25\%$ slowdown) compared to managing isolated dedicated stores (e.g., separate vector DB, document store, and graph database).
- **Hypothesis $H_1$**: A unified polymorphic schema implemented in PostgreSQL with composite indexing achieves sub-50ms multi-modal retrieval while reducing synchronization overhead, data duplication, and transaction inconsistency by $>40\%$.
- **Formal Formulation**:
  Let a unified memory record $M$ be defined as:
  $$M = \langle \text{id}, \text{tenant\_id}, \mathcal{M}, c, \vec{v}, \mathcal{T}, \mathcal{P}, \mathcal{S}, \mathcal{R} \rangle$$
  where $\mathcal{M} \in \{\text{WORKING}, \text{EPISODIC}, \text{SEMANTIC}, \text{PROCEDURAL}\}$ denotes modality, $c$ is structured content, $\vec{v} \in \mathbb{R}^d$ is the dense embedding vector, $\mathcal{T}$ is the bitemporal validity tuple, $\mathcal{P}$ is the provenance graph, $\mathcal{S}$ is the salience-utility vector, and $\mathcal{R}$ is the set of typed relational edges.
- **Empirical Validation**:
  - Benchmarked against isolated heterogeneous multi-database configurations (ChromaDB + SQLite + Neo4j) on identical workloads up to $10^6$ records.
  - Metrics: Write latency (p95, p99), multi-modal query latency (p95), transactional rollback success rate, and storage amplification ratio.

---

### Research Question 2 (RQ2): Bitemporal Interval Reasoning and Contradiction Resolution

> **Question**: *Does explicit bitemporal modeling ($[t_{start}, t_{end}]$) combined with graph-based contradiction invalidation eliminate contradictory fact hallucinations in multi-session agent reasoning?*

- **Hypothesis $H_0$**: Dense semantic retrieval augmented with metadata date filtering matches the precision of explicit bitemporal interval intersection and directed contradiction suppression.
- **Hypothesis $H_1$**: Explicit bitemporal interval intersection combined with directed contradiction suppression reduces contradictory fact retrieval by $\ge 85\%$ on multi-session knowledge update benchmarks compared to standard top-$k$ semantic retrieval.
- **Formal Formulation**:
  A fact assertion $F$ is temporally valid at query reference time $t_q$ if and only if:
  $$\text{Valid}(F, t_q) \iff (t_{valid\_from} \le t_q < t_{valid\_to}) \land \neg \exists F' \text{ s.t. } (F' \succ_{\text{supersedes}} F \land t_{asserted}(F') \le t_q)$$
  where $\succ_{\text{supersedes}}$ denotes a verified contradiction edge indicating that $F'$ replaces $F$.
- **Empirical Validation**:
  - Evaluation on the **LongMemEval** (Knowledge Update and Temporal Reasoning subsets) and **MemoryAgentBench** (Conflict Resolution / Selective Forgetting subsets).
  - Metrics: Outdated Fact Intrusion Rate (OFIR), Temporal Sequence QA Accuracy, and Abstention Precision on obsolete facts.

---

### Research Question 3 (RQ3): Adaptive Cognitive Forgetting vs. Static Accumulation

> **Question**: *How does an adaptive cognitive retention function—integrating Ebbinghaus temporal decay, access frequency, and task utility reinforcement—impact context window efficiency and retrieval signal-to-noise ratio over long-horizon agent trajectories?*

- **Hypothesis $H_0$**: Mathematical decay functions do not significantly improve downstream agent task accuracy over standard sliding FIFO windows or static vector storage with high-$k$ retrieval.
- **Hypothesis $H_1$**: An ACT-R base-level activation function with utility reinforcement increases retrieved context precision by $\ge 30\%$ while reducing prompt token consumption by $\ge 40\%$ over conversations exceeding 100 interaction sessions.
- **Formal Formulation**:
  For memory record $m$ at current time $t$:
  $$\text{Activation}(m, t) = \ln \left( \sum_{k=1}^{n} (t - t_k)^{-d} \right) + w_s \cdot \text{Salience}(m) + w_u \cdot \text{Utility}(m)$$
  where $t_k$ represents the historical access and reinforcement timestamps, $d \in (0, 1)$ is the power-law decay rate, $\text{Salience}(m) \in [0, 1]$ is intrinsic importance, and $\text{Utility}(m) \in \mathbb{R}$ is the accumulated reward feedback from successful task completions utilizing memory $m$.
  When $\text{Activation}(m, t) < \tau_{decay}$, the memory transitions from `ACTIVE` to `DECAYING`, and subsequently to `ARCHIVED`, filtering it from standard working retrieval while preserving it in historical search.
- **Empirical Validation**:
  - Evaluation on the **LoCoMo** multi-session dataset (35 sessions, 300 turns) and synthetic lifelong agent simulations ($>1,000$ turns).
  - Metrics: Prompt Token Cost per Turn, Retrieval Signal-to-Noise Ratio (SNR), Mean Reciprocal Rank (MRR) of critical ground-truth facts.

---

### Research Question 4 (RQ4): Autonomous Consolidation and Reflection Dynamics

> **Question**: *Can asynchronous memory consolidation reliably synthesize discrete episodic interactions into durable semantic knowledge triples and procedural skill definitions with bounded compute overhead and zero human intervention?*

- **Hypothesis $H_0$**: Automated consolidation introduces cumulative semantic drift and compounding hallucinations that degrade the agent's long-term knowledge graph integrity.
- **Hypothesis $H_1$**: Constraining consolidation through topological community detection (Louvain/Leiden algorithms on episodic associations) and strict schema validation produces semantic concepts with $>90\%$ factual alignment to source episodes and bounded $O(N \log N)$ compute scaling.
- **Formal Formulation**:
  Given an episodic sequence $E = \{e_1, e_2, \dots, e_N\}$ within a temporal cluster:
  $$\text{Consolidate}(E) \to \{K_{\text{semantic}}, S_{\text{procedural}}\}$$
  subject to the constraint:
  $$\forall k \in K_{\text{semantic}}, \quad \text{Support}(k, E) \ge \theta_{support} \quad \land \quad \text{Confidence}(k) \ge \theta_{confidence}$$
  with back-links $\text{Provenance}(k) = \text{IDs}(E)$.
- **Empirical Validation**:
  - Multi-session narrative summarization and task repeat benchmarks on LoCoMo and SWE-bench trajectories.
  - Metrics: Factual Consistency Score (using NLI/fact-checking baselines), Entity Deduplication Precision, and Skill Reusability Success Rate.

---

### Research Question 5 (RQ5): Cryptographic Provenance and Hallucination Suppression

> **Question**: *Does attaching explicit provenance DAGs and confidence scores to retrieved context strings enable LLMs to better calibrate answer uncertainty and abstain when information is ungrounded?*

- **Hypothesis $H_0$**: Providing provenance metadata in context prompts consumes token budget without measurably reducing factual hallucination or improving abstention accuracy.
- **Hypothesis $H_1$**: Provenance-annotated context enables agents to achieve a $\ge 50\%$ improvement in abstention accuracy on ungrounded/absent information on LongMemEval without degrading extraction accuracy on grounded facts.
- **Formal Formulation**:
  Retrieved context injected into working memory is structured as a typed citation block:
  $$C = \left\{ \langle c_i, \text{Source}: \text{prov}_i, \text{Confidence}: \sigma_i, \text{Validity}: [t_{v1}, t_{v2}] \rangle \right\}_{i=1}^K$$
  The agent prompt explicitly instructs abstention if $\max_i(\sigma_i) < \theta_{abstain}$ or if no cited memory directly entails the query.
- **Empirical Validation**:
  - LongMemEval Abstention subset and TruthfulQA agent variants.
  - Metrics: Hallucination Rate, Abstention Precision/Recall, and Citation Accuracy.

---

## 3. Summary of Research Questions & Methodological Alignment

| RQ | Core Investigation | Independent Variables | Dependent Variables | Primary Benchmark |
| :--- | :--- | :--- | :--- | :--- |
| **RQ1** | Unified Schema Efficiency | Database architecture (Unified PostgreSQL vs. Isolated Heterogeneous) | Write/Read latency, data duplication, consistency | Synthetic $10^6$ record stress test |
| **RQ2** | Bitemporal & Contradiction Resolution | Temporal model (Point-in-time vs. Bitemporal interval + Contradiction DAG) | Outdated fact intrusion rate, temporal QA accuracy | LongMemEval & MemoryAgentBench |
| **RQ3** | Adaptive Cognitive Forgetting | Forgetting policy (None, FIFO window, Exponential, ACT-R + Utility) | Retrieval SNR, prompt token cost, long-term recall | LoCoMo (35 sessions) |
| **RQ4** | Autonomous Consolidation | Consolidation algorithm (Unconstrained LLM vs. Graph Cluster + NLI verification) | Factual consistency, semantic drift rate, skill reusability | LoCoMo & Agentic trajectories |
| **RQ5** | Provenance & Calibration | Context representation (Raw text vs. Provenance-annotated citations) | Abstention precision, hallucination rate, citation fidelity | LongMemEval Abstention track |

---

## 4. Threats to Validity and Research Limitations

1. **Model Bias in Evaluation**: Evaluating memory systems using LLM-as-a-judge (e.g., GPT-4 judge) introduces systematic evaluation biases. AMARA mitigates this by relying on exact-match factual benchmarks, ground-truth entity tracking, and human-verified datasets (LoCoMo, LongMemEval).
2. **Computational Overhead of Extraction**: Automated extraction and consolidation consume LLM inference tokens. In initial releases, extraction is optional or asynchronous to prevent blocking user-facing agent loops.
3. **Database Scalability Bounds**: While PostgreSQL + pgvector provides exceptional relational and vector capabilities up to millions of records, hyperscale distributed deployments ($>10^8$ records) will eventually require specialized distributed indexing tiers (planned for future SaaS architecture).

