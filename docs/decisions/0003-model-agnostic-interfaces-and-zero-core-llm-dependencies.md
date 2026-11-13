# 3. Model-Agnostic Interfaces and Zero Core LLM Dependencies

Date: 2026-11-13  
Status: Accepted

## Context

Many agent memory frameworks tightly couple themselves to specific commercial LLM SDKs (e.g., OpenAI, Anthropic, Google GenAI) or heavy orchestration libraries (LangChain, LlamaIndex). This causes:
- Frequent dependency churn, breaking changes, and version conflicts.
- High barrier to adoption for users employing custom local models, private endpoints, or alternative inference stacks.
- Unnecessary network and telemetry bloat in core library operations.

## Decision

The core AMARA framework will maintain **zero external LLM dependencies**:
- Core data models, retrieval protocols, decay algorithms, and context synthesis interfaces will rely solely on standard Python libraries and Pydantic v2.
- Interactions requiring model inference (such as semantic summarization, entity extraction, or embedding generation) will be abstracted through caller-provided callables or provider protocols.
- Optional integration adapters (e.g. for specific embedding providers or LLM frameworks) will reside in separate optional packages or extension modules, never in `amara.core`.

## Consequences

### Positive
- True model agnosticism: Works identically with open-weights local models (via Ollama, vLLM, llama.cpp) and cloud APIs.
- Minimal dependency graph and lightning-fast installation times.
- Zero risk of vendor lock-in or unexpected remote network calls within the core engine.

### Negative / Considerations
- Integrators must supply or configure embedding/reasoning callables when advanced semantic extraction is utilized.

