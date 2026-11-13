# AMARA AI Framework Integrations Guide

AMARA (Adaptive Memory Architecture for Reasoning and AI) provides first-class integrations for modern agentic and generative AI frameworks. Rather than coupling memory to specific library runtimes, AMARA utilizes **decoupled adapter patterns** that treat external frameworks as consumers of verified cognitive context.

---

## 1. Design Principles

1. **Decoupled Architecture**: Integration nodes operate via duck-typing on standard dictionaries or Pydantic state representations. No framework-internal private state is mutated.
2. **External Context Augmentation**: In generative models (such as Hugging Face Transformers), AMARA reconstructs verified memory context strictly in prompt space. No model weights or tokenizers are modified, avoiding false claims of continual learning.
3. **Optional Dependencies**: AMARA core does not force heavy dependencies. Integrations are isolated behind optional package extras:
   ```bash
   pip install amara[langgraph]
   pip install amara[transformers]
   pip install amara[fastapi]
   pip install amara[all-integrations]
   ```
4. **Epistemic Traceability**: Every retrieved proposition preserves confidence scores, assertion timestamps, validity windows, and citation keys (`[REF-N]`).

---

## 2. LangGraph Integration

`AmaraLangGraphAdapter` integrates AMARA cognitive memory with LangGraph state graphs via reusable, composable node functions.

### Adapter Capabilities

- **`create_pre_retrieval_node`**: Extracts query from state, reconstructs relevant cognitive context, and injects `context` and `memory_citations` into graph state.
- **`create_post_extraction_node`**: Observes agent input/output, generates an episodic interaction memory, and extracts semantic propositions.
- **`create_memory_action_node`**: Executes agent-directed memory operations (e.g., explicitly remembering a rule, forgetting a fact).
- **`create_shared_project_node`**: Injects shared team standards, architectural invariants, or runbooks into state.

### Async Example

```python
from langgraph.graph import StateGraph, END
from amara.integrations.langgraph import AmaraLangGraphAdapter
from amara.sdk import MemoryEngine, MemoryConfig

engine = MemoryEngine(MemoryConfig())
await engine.initialize()

adapter = AmaraLangGraphAdapter(engine=engine, default_namespace="team_alpha")

workflow = StateGraph(dict)

# Register AMARA nodes
workflow.add_node(
    "pre_retrieval",
    adapter.create_pre_retrieval_node(
        query_key="query",
        context_key="context",
        budget_tokens=1024,
    ),
)
workflow.add_node("agent", call_llm_reasoning)
workflow.add_node(
    "post_extraction",
    adapter.create_post_extraction_node(
        input_key="query",
        output_key="response",
    ),
)

workflow.set_entry_point("pre_retrieval")
workflow.add_edge("pre_retrieval", "agent")
workflow.add_edge("agent", "post_extraction")
workflow.add_edge("post_extraction", END)

app = workflow.compile()
state = await app.ainvoke({"query": "What are our database connection limits?"})
```

---

## 3. Hugging Face Transformers Integration

`AmaraTransformersWrapper` wraps Hugging Face `pipeline` or text-generation callables with autonomous pre-generation context reconstruction.

### Key Characteristics

- **Prompt Augmentation**: Reconstructs relevant episodic and semantic propositions, formatting them into an anchor-cited block (`### AMARA Verified Cognitive Memory Context`).
- **Citation Pass-Through**: Returns `AmaraGenerationResult` containing raw generated text, formatted prompt, and structured citation metadata.
- **Zero Weight Modification**: Operates completely outside the model's parameters.
- **Optional Auto-Remember**: Automatically logs conversation turns into episodic memory.

### Usage Example

```python
from amara.integrations.huggingface import AmaraTransformersWrapper
from amara.sdk import MemoryEngine

engine = MemoryEngine()
await engine.initialize()

wrapper = AmaraTransformersWrapper(
    engine=engine,
    pipeline=hf_text_generation_pipeline,
    namespace="user_workspace",
    budget_tokens=512,
    auto_remember=True,
)

# Text generation with grounded memory injection
result = await wrapper.agenerate(
    prompt="What are my cloud deployment preferences?",
    author_id="user_123",
)

print(result.text)
print("Used citations:", len(result.citations))
```

---

## 4. FastAPI Service Integration

For distributed architectures, AMARA provides an external client, FastAPI dependency injection provider, and session tracking middleware.

### Components

1. **`AmaraClient`**: Async HTTP client communicating with hosted AMARA REST APIs (`/api/v1/*`) with built-in API key authentication, retries, and timeout control.
2. **`AmaraMemoryDependency`**: FastAPI `Depends()` factory injecting configured client instances or active namespaces into route handlers.
3. **`AmaraSessionMiddleware`**: Middleware extracting session identifiers (`X-Session-ID`) and injecting session memory headers.

### Usage Example

```python
from fastapi import FastAPI, Depends
from amara.integrations.fastapi import AmaraClient, AmaraMemoryDependency

app = FastAPI()

memory_dep = AmaraMemoryDependency(
    base_url="https://api.amara.ai",
    api_key="amara_live_secret_key",
    default_namespace="production_apps",
)


@app.post("/chat")
async def chat_endpoint(
    prompt: str,
    amara: AmaraClient = Depends(memory_dep.get_client),
):
    # Reconstruct memory for current prompt
    context_data = await amara.reconstruct_context(
        query=prompt,
        budget_tokens=512,
    )

    # Generate response with grounded memory
    llm_response = call_model(prompt=prompt, context=context_data["formatted_context"])

    # Store turn
    await amara.remember(
        content=f"User: {prompt}\nAgent: {llm_response}",
        category="episodic",
    )

    return {"response": llm_response, "citations": context_data["citations"]}
```

---

## 5. Generic Python Agent Facade

`AmaraAgentMemory` provides a lightweight, framework-agnostic cognitive memory lifecycle manager for custom autonomous agent loops.

### Capabilities

- **`before_step(prompt)`**: Retrieves grounded context before taking an action.
- **`after_step(prompt, response)`**: Persists episodic turn and extracts facts.
- **`learn_fact(fact)` / `alearn_fact(fact)`**: Directly ingests a verified semantic fact.
- **`learn_procedure(steps)` / `alearn_procedure(steps)`**: Directly ingests a procedural workflow or runbook.
- **`forget(memory_id)` / `aforget(memory_id)`**: Soft-deletes or tombstone-invalidates memory.

### Usage Example

```python
from amara.integrations.generic_agent import AmaraAgentMemory
from amara.sdk import MemoryEngine

engine = MemoryEngine()
await engine.initialize()

agent_memory = AmaraAgentMemory(
    engine=engine,
    agent_id="code_reviewer_v1",
    namespace="repo_core",
)

# Ingest engineering standard
await agent_memory.alearn_fact(
    fact="All database migrations must have a corresponding downgrade step.",
    confidence=0.98,
)


# Autonomous Agent Step
async def run_agent_loop(user_task: str):
    # 1. Retrieve context
    grounded = await agent_memory.before_step(user_task)

    # 2. Reason with grounded context
    response = execute_reasoning(task=user_task, memory=grounded.context)

    # 3. Persist step
    await agent_memory.after_step(task=user_task, response=response)
    return response
```

---

## 6. Runnable Examples Reference

The repository provides 4 standalone executable walkthrough scripts in `examples/`:

1. `examples/multi_session_chatbot.py`: Demonstrates multi-turn user profile tracking, state updates across disparate sessions, and knapsack-packed citation injection.
2. `examples/langgraph_assistant.py`: Demonstrates stateful LangGraph workflows with pre-retrieval, reasoning, and explicit memory pinning nodes.
3. `examples/project_aware_coding_assistant.py`: Demonstrates code-generation workflows constrained by ingested architectural standards, type invariants, and runbooks.
4. `examples/customer_support_assistant.py`: Demonstrates enterprise customer support triage using customer tier SLAs, designated contacts, and incident runbooks.
