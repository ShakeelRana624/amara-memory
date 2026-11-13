# AMARA 0.1.0 Commercial Release Announcement

**Date**: November 13, 2026  
**Product**: AMARA (Adaptive Memory Architecture for Reasoning and AI)  
**Version**: `0.1.0 (Commercial Production Release)`  
**Repository**: [https://github.com/ShakeelRana624/amara-memory](https://github.com/ShakeelRana624/amara-memory)  
**License**: Proprietary Commercial Software License (All Rights Reserved)  
**Contact**: [commercial@amara.ai](mailto:commercial@amara.ai) | [https://amara.ai](https://amara.ai)

---

## Announcing AMARA: The Cognitive Memory Substrate for Foundation Agents

We are proud to announce the **0.1.0 Commercial Production Release of AMARA**, an enterprise-grade cognitive memory framework and hosted context reconstruction engine engineered for autonomous AI agents, multi-agent systems, and foundation models.

Modern Large Language Models are inherently stateless. As teams push autonomous agents into long-horizon tasks, multi-session customer workflows, and enterprise automation, they face a severe trilemma:
1. **Context Window Attention Saturation**: Stuffing conversational histories into LLM context prompts triggers the "lost-in-the-middle" degradation, drives inference bills exponentially higher, and adds multi-second latency.
2. **Naive Vector RAG Shortcomings**: Standard vector databases retrieve semantically similar passages based on cosine distance. They fail catastrophically at temporal reasoning, cannot reconcile factual updates, and clobber historical records upon collisions.
3. **Absence of Cognitive Differentiation**: Human cognition separates short-term working state, autobiographical episodic events, distilled semantic truths, and procedural playbooks. Naive storage treats all text identically.

**AMARA solves this by introducing a dedicated cognitive memory architecture.**

---

## Key Capabilities & Architectural Innovations

### 1. 5-Tier Cognitive Memory Taxonomy
- **Working Memory**: Dynamic attention buffer for active execution turns, bounded by a strict session horizon.
- **Episodic Memory**: Time-indexed autobiographical event traces with full provenance and temporal anchors.
- **Semantic Memory**: Generalized facts, domain knowledge graphs, and cross-session entity relationships.
- **Procedural Memory**: Multi-step reasoning playbooks, execution schemas, and verified tool-use skills.
- **Associative Memory**: Dynamic knowledge graph edges connecting concepts, entities, and attributes.

### 2. 5-Way Bitemporal Hybrid Retrieval Engine
Combines **Dense Vector Embeddings** (ANN cosine similarity), **Lexical BM25 Matching**, **Temporal Recency Decay** ($T_{1/2}$ half-life), and **Relational Graph Walks** fused via **Reciprocal Rank Fusion (RRF)**.

### 3. Deterministic Contradiction Reconciliation
When an agent observes an updated fact (e.g., a customer switching preferred configurations), AMARA's bitemporal engine updates the validity window and marks the older assertion as superseded, preserving full historical auditability rather than blindly overwriting data.

### 4. 8-Stage Context Reconstruction Engine
Assembles token-bounded, deduplicated, chronologically coherent context packets directly consumable by agent system prompts with strict citation provenance (`[REF-1]`, `[REF-2]`).

### 5. Multi-Framework AI Integrations
Native, decoupled adapters for:
- **LangGraph**: Reusable `AmaraMemoryNode` for pre-agent context injection and post-agent reflection.
- **Hugging Face Transformers**: Clean pre-generation prompt augmentation without GPU CUDA memory interference.
- **FastAPI**: Distributed microservice client (`AmaraFastAPIClient`) with HTTP/2 connection pooling.
- **Generic Python Agents**: Turnkey `AgentMemoryLoop` for bespoke reasoning scripts.

### 6. Developer Dashboard & Modern Web Portal
Next.js 14 (App Router), TypeScript, and Tailwind CSS dashboard providing:
- Real-time Memory Explorer and Provenance Inspector.
- Visual Relationship Knowledge Graph walking.
- Interactive Retrieval Playground comparing hybrid vs. lexical vs. semantic scores.
- Dedicated AI Framework Integrations Hub with copyable code snippets.
- Cryptographic API Key provisioning with instant revocation.

---

## Empirical Benchmark Validation

AMARA was rigorously benchmarked across standardized long-term memory benchmarks (**LongMemEval**, **LoCoMo**, and **Ablation Studies**) against standard industry baselines:

| Metric | No Memory | Conversation Summary | Vector RAG | **AMARA (Ours)** | Improvement |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recall@5** | 0.000 | 0.412 | 0.684 | **0.916** | **+33.9%** |
| **nDCG@10** | 0.000 | 0.384 | 0.639 | **0.887** | **+38.8%** |
| **Temporal Accuracy** | 0.0% | 34.2% | 48.7% | **94.8%** | **+94.7%** |
| **Update Accuracy** | 0.0% | 28.5% | 36.1% | **96.2%** | **+166.5%** |
| **Prompt Token Overhead**| 0 tk | 1,840 tk (+80%) | 1,024 tk (1.0x) | **228 tk (-77.8%)** | **4.5x Savings** |
| **P95 Retrieval Latency**| 0.1 ms | 28.4 ms | 18.2 ms | **14.8 ms** | **-18.7% Faster** |

Full scientific methodology and experimental proofs are detailed in our published manuscript: [docs/research/amara-research-paper.md](docs/research/amara-research-paper.md).

---

## Production Readiness & Security Sign-Off

The AMARA 0.1.0 release has passed all release verification gates:
- **233 Passing Tests**: 100% test pass rate across unit, integration, and security test suites.
- **Strict Static Typing**: Zero `mypy` issues across 132 Python source files in strict mode.
- **Ruff Linting**: 100% compliant across 168 files.
- **Bank-Grade Security**: Proved zero cross-tenant leakage across vector, lexical, relational, and administrative boundaries. Cryptographic API keys are salted and SHA-256 hashed.
- **Empirical Load Testing**: Tested under **50 concurrent worker threads** across 600 operations with **0.00% error rate** and sub-200ms P50 ingestion latency.
- **Docker & Ingress**: Single-command deployment (`docker compose up -d`) with automated migrations and Caddy TLS 1.3 ingress.

---

## Getting Started in 60 Seconds

Run our interactive onboarding tour directly from your terminal:

```bash
git clone https://github.com/ShakeelRana624/amara-memory.git
cd amara-memory
uv venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Run interactive 60-second onboarding tour
python examples/developer_onboarding_tour.py
```

For the complete 8-stage onboarding guide, see [docs/guides/developer-onboarding.md](docs/guides/developer-onboarding.md).

---

## Commercial Enterprise Inquiries

AMARA is proprietary commercial software. All rights reserved.

For commercial licensing agreements, custom enterprise on-premise deployments, or dedicated technical support:
- **Commercial Inquiries**: [commercial@amara.ai](mailto:commercial@amara.ai)
- **Repository**: [https://github.com/ShakeelRana624/amara-memory](https://github.com/ShakeelRana624/amara-memory)
- **Copyright**: &copy; 2026 AMARA. All Rights Reserved.
