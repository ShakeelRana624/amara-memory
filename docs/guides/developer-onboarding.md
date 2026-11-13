# AMARA Developer Onboarding Guide: From Zero to Persistent Agent Memory

Welcome to AMARA (Adaptive Memory Architecture for Reasoning and AI). This guide walks you through the complete developer onboarding journey, taking your AI applications from stateless LLMs to persistent, temporally-aware cognitive systems in under 5 minutes.

---

## The 8-Stage Onboarding Journey

```
  [1. Discover] ──▶ [2. Read Docs] ──▶ [3. Install SDK] ──▶ [4. Workspace Setup]
                                                                     │
  [8. Provenance] ◀── [7. Hybrid Recall] ◀── [6. Store Memory] ◀─────┴── [5. API Keys]
```

---

### Step 1: Discovering AMARA
Unlike standard vector stores that only compute static cosine distance, AMARA is a **cognitive memory engine**. It provides:
- **5 Cognitive Memory Types**: Working, Episodic, Semantic, Procedural, and Associative.
- **Bitemporal Tracking**: Distinguishes between when an event happened vs. when the agent learned about it.
- **Deterministic Contradiction Handling**: Supersedes obsolete facts without clobbering historical records.
- **Context Reconstruction**: Generates token-bounded system prompts with citations (`[REF-1]`).

---

### Step 2: Architecture Documentation
Before diving into code, familiarize yourself with core concepts:
- [Overview & Architecture](file:///c:/Users/shake/OneDrive/Desktop/AMARA/docs/architecture/overview.md)
- [Cognitive Memory Lifecycle](file:///c:/Users/shake/OneDrive/Desktop/AMARA/docs/architecture/memory-lifecycle.md)
- [Hybrid Retrieval Pipeline](file:///c:/Users/shake/OneDrive/Desktop/AMARA/docs/architecture/retrieval-pipeline.md)

---

### Step 3: Installing the Python SDK

AMARA requires **Python 3.12+**. Install via `pip` or high-speed `uv`:

```bash
# Clone the repository
git clone https://github.com/ShakeelRana624/amara-memory.git
cd amara-memory

# Set up virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with development tooling
uv pip install -e ".[dev]"
```

Verify installation:
```bash
amara info
```

---

### Step 4: Workspace & Tenant Provisioning

AMARA isolates memories strictly by `tenant_id` and `workspace_id` at the database level:

```python
from amara.sdk import MemoryConfig, MemoryEngine

config = MemoryConfig(
    storage_backend="postgres",  # Or "memory" for local offline testing
    database_url="postgresql+asyncpg://amara:password@localhost:5432/amara_db",
    default_tenant_id="acme_corp",
    default_workspace_id="customer_support_agent",
)
```

---

### Step 5: Obtaining & Managing API Keys

When deploying AMARA as a shared cloud service or local microservice, authenticate requests via cryptographic API keys:

#### CLI Generation:
```bash
amara create-key --tenant-id acme_corp --name "Production Agent" --scopes "read,write"
```

Save the generated key (`amara_live_...`). It is hashed with SHA-256 and will never be shown again.

---

### Step 6: Storing Your First Memory (`remember`)

Ingest observations into the cognitive memory layer. AMARA automatically extracts subject-predicate-object facts, named entities, and assigns a salience score:

```python
import asyncio
from amara.sdk import MemoryEngine, MemoryConfig
from amara.models.enums import MemoryType


async def run():
    config = MemoryConfig(storage_backend="memory")  # Zero-dependency local mode
    async with MemoryEngine(config) as engine:
        # Ingest user preference (Semantic memory)
        mem = await engine.remember(
            content="Customer prefers technical markdown responses with code snippets.",
            memory_type=MemoryType.SEMANTIC,
            importance=0.90,
            confidence=0.95,
            metadata={"source": "onboarding_tour"},
        )
        print(f"Memory recorded with ID: {mem.memory_id}")


if __name__ == "__main__":
    asyncio.run(run())
```

---

### Step 7: Recalling Memories in Later Sessions (`recall` & `reconstruct`)

When the agent receives a user prompt in a future session:

```python
async def recall_example(engine):
    # 1. 5-Way Hybrid Recall (Vector + BM25 + Temporal + Relational)
    results = await engine.recall(
        query="What format does the user prefer for answers?",
        top_k=3,
    )
    for r in results:
        print(f"Match [{r.relevance_score:.2f}]: {r.content}")

    # 2. Context Reconstruction for System Prompt Injection
    context = await engine.reconstruct(
        query="Prepare response for customer query",
        budget=500,  # Strict token budget
    )
    print("\n--- Injected System Prompt Context ---")
    print(context.formatted_context)
    print(f"Tokens consumed: {context.total_tokens_used} / 500")
```

---

### Step 8: Exploring Provenance, Knowledge Graphs & Lifecycle in Dashboard

Launch the AMARA developer dashboard:

```bash
cd dashboard
npm install
npm run dev
# Navigate to http://localhost:3000
```

1. **Memory Explorer** (`/dashboard/memories`): Search, filter, and inspect memories.
2. **Provenance Inspector** (`/dashboard/memories/[id]`): Review exact fact triples, source hashes, and assertion timestamps.
3. **Relationship Graph** (`/dashboard/relationships`): Visually walk entity-relationship graph edges.
4. **Retrieval Playground** (`/dashboard/retrieval`): Interactively compare semantic vs. lexical vs. hybrid recall scores in real time.
5. **Integrations Hub** (`/dashboard/integrations`): Copy ready-to-use adapters for LangGraph, Hugging Face, and FastAPI.
