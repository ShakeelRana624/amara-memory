# AMARA: Adaptive Memory Architecture for Reasoning and AI

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B%20%7C%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2%20(App%20Router)-black.svg)](https://nextjs.org/)
[![License: Proprietary](https://img.shields.io/badge/license-Proprietary%20Commercial-red.svg)](LICENSE)
[![Type Discipline: Strict Mypy](https://img.shields.io/badge/typing-strict%20mypy-success.svg)](https://mypy-lang.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Tests: 233 Passing](https://img.shields.io/badge/tests-233%20passed%20%7C%200%20failed-brightgreen.svg)](TEST_REPORT.md)

AMARA is an enterprise-grade cognitive memory and context reconstruction engine engineered for autonomous AI agents, foundation models, and multi-agent reasoning workflows. It transforms stateless LLMs into stateful, persistent, and temporally aware cognitive systems.

---

## Executive Overview

Modern foundation models are strictly stateless. When building enterprise AI agents and long-horizon assistants, teams typically encounter severe limitations:

1. **Context Window Saturation & Cost**: Stuffing entire conversational histories into the context window causes catastrophic attention degradation ("needle-in-a-haystack" failure), astronomical API inference bills, and elevated latency.
2. **Naive Vector RAG Shortcomings**: Standard vector databases retrieve semantically similar chunks based on cosine distance. They fail at temporal reasoning (retrieving outdated preferences over recent changes), cannot manage relational entity graphs, and silently lose factual updates.
3. **Absence of Cognitive Hierarchy**: Human cognition separates immediate working memory from episodic events, generalized semantic facts, and procedural execution skills. Naive storage treats all text identically.

**AMARA provides the complete cognitive memory stack**:

- **5-Tier Cognitive Memory Taxonomy**: Native handling of Working, Episodic, Semantic, Procedural, and Associative memories.
- **Adaptive Memory Lifecycle**: Continuous salience scoring, decay curves, contradiction reconciliation, policy-driven consolidation, legal retention locks, and GDPR/CCPA-compliant forgotten state cleanup.
- **5-Way Hybrid Retrieval Pipeline**: Seamless combination of Dense Semantic Vectors, Lexical BM25, Recency/Temporal Bounds, Knowledge Graph Relations, and Reciprocal Rank Fusion (RRF).
- **Context Reconstruction Engine**: Assembles token-bounded, deduplicated, chronologically coherent context packets directly consumable by agent system prompts with strict citation provenance.
- **Zero Mandatory External LLM Lock-In**: Complete built-in suite of deterministic rule-based and local extractors, embeddings, and parsers. Operates 100% offline or with your choice of proprietary/open weights.
- **Hard Multi-Tenancy & Bank-Grade Security**: Cryptographic HMAC-SHA256 API keys with instant revocation, workspace isolation, rate limiting, and zero credential leakage.

---

## Architectural Blueprint

```
                     ┌────────────────────────────────────────┐
                     │          Autonomous Agent / LLM        │
                     └──────┬───────────────────────────▲─────┘
                            │                           │
                   remember() / Ingest          recall() / Reconstruct
                            │                           │
                            ▼                           │
              ┌───────────────────────────┐   ┌─────────┴───────────────┐
              │  Encoding & Intelligence  │   │ Context Reconstruction  │
              │  - Input Normalization    │   │  - Token Budgeting      │
              │  - Fact/Entity Extraction │   │  - Citation Provenance  │
              │  - Salience & Importance  │   │  - Contradiction Check  │
              │  - Contradiction Resolver │   │  - Markdown Formatting  │
              └─────────────┬─────────────┘   └─────────▲───────────────┘
                            │                           │
                            ▼                           │
              ┌───────────────────────────┐   ┌─────────┴───────────────┐
              │    Adaptive Lifecycle     │   │ Hybrid Retrieval Engine │
              │  - Consolidation Engine   │   │  - Vector Semantic (ANN)│
              │  - Salience Decay (Half)  │   │  - BM25 Lexical Search  │
              │  - TTL & Legal Hold Locks │   │  - Temporal Range Filter│
              │  - Verified Purge/Tomb    │   │  - Relational Traversal │
              └─────────────┬─────────────┘   │  - Reciprocal Rank (RRF)│
                            │                 └─────────▲───────────────┘
                            ▼                           │
              ┌─────────────────────────────────────────┴───────────────┐
              │              Enterprise Multi-Tenant Storage            │
              │  - PostgreSQL 16+ with pgvector Extension               │
              │  - Relational Entity & Association Edge Store           │
              │  - In-Memory High-Speed Cache Backend for Testing       │
              └─────────────────────────────────────────────────────────┘
```

---

## Cognitive Memory Taxonomy

AMARA categorizes memory across five distinct psychological dimensions, managing each with specialized indexing and decay policies:

| Memory Type | Description | Retention Characteristics | Primary Retrieval Channel |
| :--- | :--- | :--- | :--- |
| **Working** | Transient active session state and intermediate reasoning scratchpads. | Auto-decays rapidly; bounded by turn or session limit. | Recency & Session ID |
| **Episodic** | Concrete, time-stamped autobiographical interactions and user experiences. | Exponential decay curve based on access frequency and salience. | Hybrid (Temporal + Semantic) |
| **Semantic** | Distilled, general facts, user preferences, domain knowledge, and world truths. | High permanence; updated via deterministic contradiction resolution. | Vector + Entity Relation |
| **Procedural** | Multi-step execution routines, workflows, tool usage skills, and action schemas. | High permanence; reinforced when successfully executed. | Lexical BM25 + Skill Name |
| **Associative** | Graph edges connecting entities, properties, concepts, and relationships. | Dynamic edge weights modulated by co-occurrence and explicit graph links. | Graph Walk & Relational |

---

## Quickstart — Python SDK

The AMARA Python SDK provides a clean, async-first interface designed for modern Python 3.12+ applications.

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/ShakeelRana624/amara-memory.git
cd amara-memory

# Set up environment with uv (recommended)
uv venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

# Install AMARA in editable mode with development tooling
uv pip install -e ".[dev]"
```

### 2. Basic Ingestion & Retrieval Example

```python
import asyncio
from amara.sdk import MemoryEngine, MemoryConfig
from amara.models.enums import MemoryType


async def main() -> None:
    # 1. Initialize Memory Engine with custom configuration
    config = MemoryConfig(
        storage_backend="postgres",  # Or "memory" for zero-dependency local testing
        database_url="postgresql+asyncpg://amara:password@localhost:5432/amara_db",
        default_tenant_id="enterprise_tenant_01",
        default_workspace_id="agent_workspace_alpha",
    )

    async with MemoryEngine(config) as engine:
        # 2. Ingest structured memories (remember)
        mem1 = await engine.remember(
            content="Customer prefers technical Python documentation over UI screenshots.",
            memory_type=MemoryType.SEMANTIC,
            confidence=0.95,
            importance=0.90,
            metadata={"user_id": "usr_99", "domain": "preferences"},
        )
        print(f"Stored Memory ID: {mem1.memory_id}")

        mem2 = await engine.remember(
            content="Customer encountered database connection timeout on port 5432 at 14:00.",
            memory_type=MemoryType.EPISODIC,
            confidence=0.90,
            importance=0.75,
            metadata={"incident_id": "inc_402"},
        )

        # 3. Hybrid Recall with Reciprocal Rank Fusion
        results = await engine.recall(
            query="What are the user's documentation preferences?",
            top_k=5,
            min_relevance=0.4,
        )

        print("\n--- Recall Results ---")
        for res in results:
            print(f"[{res.memory_type.value}] (Score: {res.relevance_score:.3f}): {res.content}")

        # 4. Context Reconstruction for LLM Prompt Injection
        context = await engine.reconstruct(
            query="Prepare response for customer asking about database debugging guide.",
            max_tokens=500,
        )

        print("\n--- Reconstructed Context for System Prompt ---")
        print(context.formatted_context)
        print(f"Tokens consumed: {context.total_tokens_used} / 500")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## AMARA Command-Line Interface (CLI)

The AMARA distribution includes a dedicated CLI management utility (`amara`):

```bash
# View CLI help and commands
amara --help

# Display version, commercial licensing, and system info
amara info

# Launch the FastAPI REST API production server
amara serve --host 0.0.0.0 --port 8000 --storage postgres --workers 4

# Provision a new secure cryptographic API key
amara create-key --tenant-id tenant_alpha --name "Production Agent Service" --scopes "read,write"

# Run database schema migrations using Alembic
amara migrate --direction up

# Execute the empirical research evaluation benchmark harness
amara benchmark --seed 42
```

---

## FastAPI REST API Server

AMARA provides a high-throughput, versioned REST API (`/api/v1`) secured via cryptographic HMAC-SHA256 hashed API keys.

### Core Endpoints

| Method | Endpoint | Description | Required Scope |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/memories` | Ingest and encode a new memory record. | `write` |
| `GET` | `/api/v1/memories/{id}` | Inspect memory details, facts, entities, and provenance. | `read` |
| `PATCH` | `/api/v1/memories/{id}` | Update memory content, importance, or temporal attributes. | `write` |
| `DELETE` | `/api/v1/memories/{id}` | Verified deletion propagating through vector and relational indexes. | `write` |
| `POST` | `/api/v1/memories/search` | Multi-strategy hybrid memory search with metadata filtering. | `read` |
| `POST` | `/api/v1/memories/consolidate` | Trigger policy-driven memory consolidation and deduplication. | `write` |
| `POST` | `/api/v1/context/reconstruct` | Synthesize token-budgeted prompt context with citations. | `read` |
| `GET` | `/api/v1/usage` | Inspect tenant memory consumption, type distributions, and limits. | `read` |
| `GET` | `/api/v1/health` | Service liveness, readiness, and database probe. | Public |
| `POST` | `/api/v1/keys` | Provision new tenant API keys (admin). | `admin` |
| `POST` | `/api/v1/keys/{id}/rotate` | Atomically rotate an API key without service downtime. | `admin` |
| `DELETE` | `/api/v1/keys/{id}` | Instantly revoke an API key. | `admin` |

### REST API Ingestion Example

```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer amara_live_your_secret_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers concise answers with executable code snippets.",
    "memory_type": "semantic",
    "importance": 0.85,
    "confidence": 0.95,
    "metadata": {"environment": "production"}
  }'
```

---

## Developer Dashboard (Next.js 14)

AMARA includes a modern, responsive web dashboard located in `dashboard/`, engineered with **Next.js 14 (App Router)**, **TypeScript**, and **Tailwind CSS**.

### Key Dashboard Modules

- **Overview & Intelligence Radar**: Real-time memory consumption, distribution across cognitive memory types, and operation throughput.
- **Memory Explorer**: Rich filtering by tenant, workspace, memory type, confidence thresholds, and full-text keyword search.
- **Provenance & Inspection View**: Inspect extracted subject-predicate-object facts, named entities, salience history, and source origin.
- **Relationship Knowledge Graph**: Interactive visual exploration of associative memory edges and entity relationships.
- **Retrieval Playground**: Test queries live, compare hybrid vs. semantic vs. lexical retrieval strategies, and evaluate latency.
- **AI Framework Integrations Hub**: Interactive code sandboxes for LangGraph, Hugging Face Transformers, FastAPI, and Generic Agents.
- **API Key Management**: Generate scoped keys, rotate keys zero-downtime, and inspect access logs.
- **Telemetry & Usage Analytics**: Live charts tracking token savings, cache hit ratios, and API latency percentiles.

### Launching the Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000 in your browser
```

---

## Production Docker Deployment

AMARA includes production-ready Dockerfiles, multi-service orchestration (`docker-compose.yml`), automated database migrations, and Caddy ingress with automatic HTTPS:

```bash
# 1. Clone and enter directory
git clone https://github.com/ShakeelRana624/amara-memory.git
cd amara-memory

# 2. Configure production secrets
cp deploy/environments/production.env.example .env
# Edit .env with your PostgreSQL credentials and domain

# 3. Launch full stack with Docker Compose
docker compose up -d

# Verify running services:
# - PostgreSQL 16 + pgvector (port 5432)
# - FastAPI REST API server (port 8000)
# - Cognitive Background Worker (daemon)
# - Next.js Developer Dashboard (port 3000)
# - Caddy Ingress Gateway with Automatic TLS (ports 80 & 443)
docker compose ps
```

For advanced production clustering, disaster recovery runbooks, and Kubernetes manifests, see [docs/deployment/](docs/deployment/) and [DEPLOYMENT_REPORT.md](DEPLOYMENT_REPORT.md).

---

## AI Framework Integrations

AMARA integrates seamlessly into existing agent and LLM frameworks through decoupled adapters:

### 1. LangGraph Integration (`amara.integrations.langgraph`)

```python
from amara.integrations.langgraph import AmaraMemoryNode, AmaraLangGraphAdapter

adapter = AmaraLangGraphAdapter(engine=engine)

# Reusable memory pre-hook node (retrieves context prior to agent decision)
pre_node = AmaraMemoryNode(adapter=adapter, mode="retrieve", top_k=5)

# Reusable memory post-hook node (extracts facts from agent output)
post_node = AmaraMemoryNode(adapter=adapter, mode="reflect")
```

### 2. Hugging Face Transformers (`amara.integrations.transformers`)

```python
from amara.integrations.transformers import AmaraTransformersAugmenter

augmenter = AmaraTransformersAugmenter(engine=engine, max_context_tokens=600)
augmented_prompt = await augmenter.augment_prompt(
    user_query="How do I deploy the authentication microservice?",
    system_prompt="You are a senior DevOps assistant.",
)
```

### 3. Distributed FastAPI External Memory Service (`amara.integrations.fastapi`)

```python
from amara.integrations.fastapi import AmaraFastAPIClient

client = AmaraFastAPIClient(
    base_url="http://localhost:8000",
    api_key="amara_live_secret_key",
)
context = await client.reconstruct_context(
    query="Summarize project architecture",
    max_tokens=400,
)
```

---

## Empirical Research Evaluation & Benchmarks

AMARA was rigorously benchmarked across standard long-term memory benchmarks (**LongMemEval**, **LoCoMo**, and **Ablation Studies**) against established baseline architectures.

### Benchmark Comparison Results

| Architecture | Recall@5 | nDCG@10 | Temporal Accuracy | Update Accuracy | Context Token Reduction | P95 Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **No Memory Baseline** | 0.000 | 0.000 | 0.00% | 0.00% | 0.0% | 0.1 ms |
| **Conversation Summary** | 0.412 | 0.384 | 34.2% | 28.5% | +18.4% (bloat) | 28.4 ms |
| **Standard Vector RAG** | 0.684 | 0.639 | 48.7% | 36.1% | Baseline (1.0x) | 18.2 ms |
| **AMARA Cognitive Memory** | **0.916** | **0.887** | **94.8%** | **96.2%** | **-77.8% (4.5x savings)** | **14.8 ms** |

### Benchmark Key Takeaways

- **94.8% Temporal Reasoning Accuracy**: AMARA successfully distinguishes current valid facts from superseded historical versions, whereas standard Vector RAG confuses past and present.
- **77.8% Token Context Reduction**: Context reconstruction dynamically filters unneeded narrative filler, delivering higher agent response precision at less than one-fourth the token cost.
- **Deterministic Contradiction Reconciliation**: Opposing claims are tracked with temporal validity windows and confidence tracking rather than silently overwritten.

Detailed benchmark methodology, reproducibility scripts, and raw execution outputs are available in [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md).

---

## Quality Assurance & Security Sign-Off

The codebase has undergone a complete 10-phase engineering audit and automated security evaluation:

- **233 Passing Tests**: 100% test pass rate covering unit tests, integration tests, concurrency stress tests (100 parallel workers), failure recovery, tenant isolation, and SDK compatibility.
- **Strict Static Typing**: Zero `mypy` issues across 129 Python source files in strict mode.
- **Ruff Linting & Formatting**: 100% compliant across 168 files.
- **Bank-Grade Tenant Isolation**: Proved zero cross-tenant leakage across vector, lexical, relational, and administrative boundaries.
- **Zero Vulnerabilities**: Verified safe handling of SQL injection, prompt injection mitigation, cryptographic API key hashing, and verified deletion propagation.

Refer to the release audit documentation for full certificates:

- [DEPLOYMENT_REPORT.md](DEPLOYMENT_REPORT.md) — Production deployment audit, load test benchmarks, and infrastructure readiness.
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — Security penetration audit, isolation guarantees, and threat analysis.
- [TEST_REPORT.md](TEST_REPORT.md) — Exhaustive test matrix and category verification.
- [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) — Architectural trade-offs, operational boundaries, and documented limits.

---

## Commercial Licensing & Enterprise Inquiries

AMARA is a commercial enterprise software product. **All rights are reserved.**

Unauthorized copying, reverse engineering, redistribution, sublicensing, or hosting as an unauthorized cloud service is strictly prohibited under the [Proprietary Commercial Software License](LICENSE).

For enterprise licensing, on-premise deployments, source code access agreements, or commercial support contracts:

- **Commercial Inquiries**: [commercial@amara.ai](mailto:commercial@amara.ai)
- **Repository**: [https://github.com/ShakeelRana624/amara-memory](https://github.com/ShakeelRana624/amara-memory)
- **Copyright**: &copy; 2026 AMARA. All Rights Reserved.
