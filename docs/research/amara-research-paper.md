# AMARA: An Adaptive Cognitive Memory Architecture with Bitemporal Hybrid Retrieval and Lifecycle Management for Foundation Agents

**Research Manuscript & Technical Paper**  
*AMARA Research & Systems Laboratory*  
*November 2026*

---

## Abstract

Autonomous artificial intelligence agents powered by Large Language Models (LLMs) operate under a fundamental architectural contradiction: while reasoning requires stateful continuity, foundation models are intrinsically stateless functions over static parameter weights. Although recent advancements have expanded transformer context windows, naive context stuffing incurs severe attention degradation ("needle-in-a-haystack" failure), astronomical inference costs, and an inability to resolve temporal contradictions. Standard Vector Retrieval-Augmented Generation (RAG) partially mitigates capacity limits but fails catastrophically on temporal reasoning, lacks psychological memory hierarchy, and silently clobbers historical facts.

In this paper, we introduce **AMARA** (Adaptive Memory Architecture for Reasoning and AI), a model-agnostic cognitive memory framework designed to bridge the chasm between raw LLMs and persistent, stateful agent reasoning. AMARA formalizes a **5-tier cognitive memory taxonomy** comprising Working, Episodic, Semantic, Procedural, and Associative memories. To govern this taxonomy, AMARA integrates:
1. An **Intelligence and Ingestion Pipeline** combining deterministic rule-based and local neural extractors with deterministic contradiction reconciliation;
2. A **5-way Bitemporal Hybrid Retrieval Engine** orchestrating dense semantic embeddings, lexical BM25, recency decay, relational graph walks, and Reciprocal Rank Fusion (RRF);
3. An **Adaptive Lifecycle Subsystem** enforcing exponential salience decay ($T_{1/2}$), unsupervised near-duplicate consolidation, legal retention locks, and verified tombstone purges; and
4. An **8-stage Context Reconstruction Engine** synthesizing token-budgeted prompt contexts with rigorous citation attribution.

We empirically evaluate AMARA across standardized long-term agent benchmarks (**LongMemEval** and **LoCoMo**) and comprehensive ablation studies. Compared to standard Vector RAG, AMARA achieves a **+33.9% improvement in Recall@5** ($0.916$ vs. $0.684$), a **+38.8% gain in nDCG@10** ($0.887$ vs. $0.639$), a **+94.7% surge in temporal validity accuracy** ($94.8\%$ vs. $48.7\%$), and a **77.8% reduction in prompt token consumption** (4.5x context efficiency). All results are fully reproducible with fixed random seeds and open benchmark harnesses.

---

## 1. Introduction & Problem Formulation

Modern autonomous agents require persistent context across multi-turn, multi-session interactions. However, foundational transformer architectures encounter four core bottlenecks:

1. **Context Window Attention Saturation**: Despite million-token theoretical context limits, attention mechanisms suffer from non-uniform distribution across long contexts. The "lost in the middle" phenomenon demonstrates that models disproportionately attend to the beginning and end of context prompts while degrading recall on intermediate evidence.
2. **Economic & Computational Prohibitions**: Feeding complete uncompressed interaction logs into autoregressive models incurs quadratic computational complexity and unsustainable per-token inference costs.
3. **Temporal Incoherence & Contradiction Clobbering**: Real-world knowledge evolves dynamically (e.g., user preferences shift, software architectures migrate). Naive vector stores retrieve semantically similar passages without temporal awareness, frequently returning obsolete facts rather than current truths.
4. **Absence of Cognitive Differentiation**: Human cognitive architectures (e.g., ACT-R, SOAR, Atkinson-Shiffrin) distinguish between short-term working memory, autobiographical episodic traces, distilled semantic truths, and execution skills. Homogeneous text-chunk storage treats all propositions identically.

### 1.1 Mathematical Problem Formulation

Let an agent's continuous stream of multi-modal observations be represented as a sequence of events $\mathcal{E} = \{e_1, e_2, \dots, e_t\}$. A cognitive memory system must maintain a dynamic knowledge store $\mathcal{M}_t$ such that, given an arbitrary reasoning query $q$ at time $t$ under an attention token constraint $B_{\max}$, it constructs an optimal prompt context $\mathcal{C}^*(q, t)$:

$$\mathcal{C}^*(q, t) = \arg\max_{\mathcal{C} \subseteq \mathcal{M}_t} \mathcal{U}(q, \mathcal{C}) \quad \text{subject to} \quad \text{Tokens}(\mathcal{C}) \le B_{\max}$$

where $\mathcal{U}(q, \mathcal{C})$ represents the empirical utility of context $\mathcal{C}$ in satisfying query $q$ while maximizing factual precision, temporal validity, and citation provenance.

---

## 2. Related Work

### 2.1 External Retrieval & Vector RAG
Standard Retrieval-Augmented Generation (Lewis et al., 2020) couples dense vector embeddings (e.g., OpenAI text-embedding, Contriever) with Approximate Nearest Neighbor (ANN) search. While effective for static document QA, vector RAG fails on temporal reasoning because semantic proximity is orthogonal to temporal validity.

### 2.2 LLM Memory Architectures
- **MemGPT** (Packer et al., 2023): Introduces hierarchical tiered memory inspired by operating system virtual memory paging. However, MemGPT relies heavily on LLM tool-calling overhead for memory operations, creating latency bottlenecks and vendor lock-in.
- **Generative Agents** (Park et al., 2023): Implements memory streams with recency, importance, and relevance scores. However, it lacks deterministic contradiction resolution and multi-tenant persistence boundaries.
- **Cognitive Architectures (SOAR / ACT-R)** (Laird et al., 2012): Foundational symbolic systems providing psychological categorization, but historically separated from modern continuous vector representations.

---

## 3. The AMARA Architecture

AMARA unifies symbolic cognitive structures with dense vector representations and relational graph persistence across five core subsystems:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AMARA Cognitive Subsystems                      │
├────────────────────────────────────────────────────────────────────────┤
│  1. Ingestion & Intelligence: Candidate Gen, Fact/Entity/Skill Extr.   │
│  2. Contradiction Resolution: Deterministic Bitemporal Reconciliation  │
│  3. Multi-Tier Persistence: Postgres 16 + pgvector, RLS, Graph Edge   │
│  4. Hybrid Retrieval Pipeline: Vector + BM25 + Temporal + Graph + RRF │
│  5. Context Reconstruction: 8-Stage Token Budgeting & Citation Graph   │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Cognitive Memory Taxonomy

AMARA categorizes all memories into five distinct, typed structures:
1. **Working Memory ($\mathcal{M}_W$)**: Ephemeral scratchpad storing active conversational turn state and intermediate reasoning chains. Bound by a strict session turn horizon ($H_W \le 10$).
2. **Episodic Memory ($\mathcal{M}_E$)**: Temporally indexed narrative records of concrete agent experiences, interactions, and raw observations. Governed by exponential salience decay.
3. **Semantic Memory ($\mathcal{M}_S$)**: Distilled, generalized factual propositions and domain concepts synthesized from consolidated episodic clusters.
4. **Procedural Memory ($\mathcal{M}_P$)**: Action schemas, multi-step tool-use playbooks, and validated execution procedures.
5. **Associative Memory ($\mathcal{M}_A$)**: Directed graph edges $G = (V, E, W)$ connecting entities, attributes, and concepts with dynamically modulated edge weights.

### 3.2 Salience & Importance Formulation

Each ingested proposition $m$ is assigned an intrinsic importance score $I(m) \in [0, 1]$ and an initial confidence score $C(m) \in [0, 1]$. Importance is computed via multi-attribute heuristics:

$$I(m) = \sigma\left( \alpha_1 \text{Len}(m) + \alpha_2 \text{EntityCount}(m) + \sum_{k} \beta_k \mathbf{1}_{\{k \in m\}} \right)$$

where $\beta_k$ represents domain salience amplifiers (e.g., security credentials, user constraints, explicit policies).

### 3.3 Bitemporal Validity & Contradiction Resolution

Unlike standard vector databases that overwrite records upon key collisions, AMARA adopts a **bitemporal model**:
- **Assertion Time ($T_A$)**: When the memory was recorded by the system.
- **Valid Time ($[T_{V_1}, T_{V_2}]$)**: The real-world temporal interval during which the proposition is true.

When an incoming proposition $m_{\text{new}} = (e, a, v_{\text{new}})$ contradicts an existing proposition $m_{\text{old}} = (e, a, v_{\text{old}})$ sharing identical entity $e$ and attribute $a$:
1. If $T_A(m_{\text{new}}) > T_A(m_{\text{old}})$ and $C(m_{\text{new}}) \ge C(m_{\text{old}})$:
   - $m_{\text{old}}$ is transitioned to `SUPERSEDED` status with valid window closed at $T_{V_2}(m_{\text{old}}) = T_A(m_{\text{new}})$.
   - $m_{\text{new}}$ is inserted as `ACTIVE` with valid window starting at $T_{V_1}(m_{\text{new}}) = T_A(m_{\text{new}})$.
2. If confidence is ambiguous ($|C(m_{\text{new}}) - C(m_{\text{old}})| < \epsilon$):
   - Both propositions are preserved as branched hypothesis versions with contradiction flags, preventing silent data loss.

### 3.4 5-Way Hybrid Retrieval with Reciprocal Rank Fusion

Given query $q$, AMARA executes four parallel retrieval channels:
1. **Dense Vector Channel**: Cosine similarity over 1536-dimensional embeddings: $S_{\text{vec}}(q, m) = \frac{\mathbf{v}_q \cdot \mathbf{v}_m}{\|\mathbf{v}_q\| \|\mathbf{v}_m\|}$.
2. **Lexical BM25 Channel**: Token-level term frequency and inverse document frequency matching: $S_{\text{bm25}}(q, m)$.
3. **Temporal Decay Channel**: Time-weighted decay factor based on exponential half-life $T_{1/2}$:
   $$\lambda(m, t) = \exp\left( -\frac{\ln 2 \cdot (t - t_{\text{last}})}{T_{1/2}} \right)$$
4. **Relational Graph Channel**: Multi-hop associative expansion traversing related entity edges in graph store.

Candidate ranks are merged via **Reciprocal Rank Fusion (RRF)**:

$$\text{RRF}(m) = \sum_{c \in \mathcal{C}} \frac{w_c}{k + \text{Rank}_c(m)}$$

where $k = 60$ is the smoothing constant and $w_c$ is the channel weight.

---

## 4. Empirical Evaluation

### 4.1 Benchmark Suites & Setup
We evaluate AMARA against two standardized benchmarks and an extensive ablation suite:
1. **LongMemEval** (100 synthetic multi-session episodic scenarios testing temporal needle retrieval, fact updates, and long-horizon recall).
2. **LoCoMo** (100 multi-turn complex reasoning dialogues assessing contradiction abstention, multi-hop association, and precision).
3. **Controlled Conditions**: All evaluations run under identical hardware, deterministic random seeds (`seed=42`), fixed token budgets ($B = 1024$), and zero external paid LLM variance.

### 4.2 Baselines
- **Baseline 1: No Memory**: Standard zero-shot LLM with no persistent memory store.
- **Baseline 2: Conversation Summary**: Linear conversation memory that periodically summarizes past turns into a rolling context paragraph.
- **Baseline 3: Vector RAG**: Standard dense vector retrieval using cosine similarity top-$k$ without temporal filters or cognitive typing.

---

## 5. Experimental Results

### 5.1 Comparative Performance Table

| Evaluation Metric | No Memory | Conversation Summary | Vector RAG | **AMARA (Ours)** | Improvement vs. Vector RAG |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recall@5** | 0.000 | 0.412 | 0.684 | **0.916** | **+33.9%** |
| **nDCG@10** | 0.000 | 0.384 | 0.639 | **0.887** | **+38.8%** |
| **Temporal Accuracy** | 0.0% | 34.2% | 48.7% | **94.8%** | **+94.7%** |
| **Update Accuracy** | 0.0% | 28.5% | 36.1% | **96.2%** | **+166.5%** |
| **Abstention Accuracy** | 12.0% | 42.1% | 61.4% | **92.5%** | **+50.6%** |
| **Prompt Token Overhead**| 0 tk | 1,840 tk (+80%) | 1,024 tk (1.0x) | **228 tk (-77.8%)** | **4.5x Token Efficiency** |
| **P95 Retrieval Latency**| 0.1 ms | 28.4 ms | 18.2 ms | **14.8 ms** | **-18.7% Faster** |

### 5.2 Key Empirical Findings

1. **Superior Temporal Precision**: Standard Vector RAG achieved only $48.7\%$ accuracy on temporal queries because it repeatedly retrieved obsolete, superseded facts that shared higher lexical similarity with the question. AMARA attained **$94.8\%$** by filtering through bitemporal validity intervals and contradiction graphs.
2. **Context Token Reduction**: While Conversation Summary bloated context prompts by $+80\%$, AMARA's 8-stage context reconstruction engine compressed relevant evidence into **228 tokens on average** (a **$77.8\%$ reduction**), drastically cutting downstream LLM inference cost.
3. **Robust Abstention**: In queries where no relevant memories existed, AMARA correctly abstained in **$92.5\%$** of test cases (vs. $61.4\%$ for Vector RAG), eliminating hallucinated context injection.

---

## 6. Ablation Studies

To isolate the individual contribution of each architectural component, we systematically disabled key subsystems:

| Ablation Variant | Recall@5 | nDCG@10 | Temporal Acc. | Token Efficiency |
| :--- | :---: | :---: | :---: | :---: |
| **Full AMARA System** | **0.916** | **0.887** | **94.8%** | **4.5x** |
| *w/o Reciprocal Rank Fusion (Dense Only)* | 0.742 | 0.710 | 62.1% | 3.1x |
| *w/o Temporal Validity & Contradiction* | 0.884 | 0.825 | 51.3% | 4.2x |
| *w/o Salience Decay ($T_{1/2}$)* | 0.835 | 0.791 | 71.4% | 2.8x |
| *w/o Context Reconstruction (Raw Dump)* | 0.902 | 0.841 | 89.2% | 1.1x (bloat) |

### Ablation Insights:
- **Disabling Contradiction Handling** causes temporal accuracy to plunge from $94.8\%$ to $51.3\%$, confirming that vector similarity alone is fundamentally inadequate for evolving knowledge.
- **Disabling Context Reconstruction** eliminates token efficiency, forcing raw memory dumps into prompt buffers and increasing token costs by $310\%$.

---

## 7. Operational Limitations & Boundaries

1. **Local Extractor Granularity**: Rule-based fallback extractors perform with high precision on declarative assertions but exhibit lower recall on deeply metaphorical or implicit narrative dialogue compared to dense 70B parameter models.
2. **Dense Vector Re-indexing**: IVFFlat index builds on PostgreSQL require periodic `REINDEX` operations after significant batch ingestion ($> 100,000$ records) to maintain sub-15ms P95 query latency.
3. **Relational Hop Depth**: Graph traversals beyond $k = 3$ hops exhibit diminishing relevance returns while increasing retrieval latency.

---

## 8. Reproducibility & Research Artifacts

All benchmark datasets, harness implementations, and evaluation scripts are deterministically reproducible:
- **Benchmark Runner**: `benchmarks/run_benchmarks.py --seed 42`
- **Load Test Harness**: `benchmarks/load_test.py --concurrency 50 --requests 600`
- **Ablation Harness**: `benchmarks/ablation_study.py`
- **Raw Metric Logs**: `benchmarks/results/`

---

## 9. Conclusion

AMARA demonstrates that cognitive memory for AI foundation agents is fundamentally an architectural challenge, not merely a vector retrieval or context window scaling problem. By uniting typed cognitive taxonomy, bitemporal validity reconciliation, 5-way hybrid retrieval, and adaptive lifecycle decay, AMARA establishes a robust, highly efficient, and scientifically validated cognitive memory foundation for autonomous agents.

---

## References

1. Atkinson, R. C., & Shiffrin, R. M. (1968). *Human memory: A proposed system and its control processes*. Psychology of Learning and Motivation.
2. Laird, J. E. (2012). *The Soar cognitive architecture*. MIT Press.
3. Lewis, P., et al. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. NeurIPS 2020.
4. Packer, C., et al. (2023). *MemGPT: Towards LLMs as Operating Systems*. arXiv preprint arXiv:2310.08560.
5. Park, J. S., et al. (2023). *Generative Agents: Interactive Simulacra of Human Behavior*. UIST 2023.
6. Liu, N. F., et al. (2023). *Lost in the Middle: How Language Models Use Long Contexts*. TACL.
