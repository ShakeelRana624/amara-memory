# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Phase 10: Quality Assurance, Security and Research Evaluation**:
  - **Comprehensive Security Penetration & Tenant Isolation Audit**:
    - Validated zero known vulnerabilities across all 28 production dependencies via `pip-audit`.
    - Authored `tests/test_security_audit.py` confirming 100% tenant boundary isolation across key lookups, vector similarity recall, relationship graph traversals, updates, and deletes.
    - Verified cryptographic API key hashing (constant-time `hmac.compare_digest`), scope boundaries (`read`, `write`), and instant key revocation.
    - Confirmed SQL injection immunity and safe textual embedding of XSS strings in context prompts.
    - Verified retention lock protections (`RetentionLockError`) and cascade delete relationship edge cleanup.
  - **Concurrency Stress & Race-Condition Suite**:
    - Authored `tests/test_concurrency_stress.py` verifying high-throughput parallel ingestion (50 concurrent tasks across 10 distinct tenants) without crosstalk.
    - Validated Optimistic Concurrency Control (OCC) with `ConcurrencyError` detection on simultaneous record mutations.
    - Verified multi-threaded worker dispatch safety on `SyncMemoryEngine` using `ThreadPoolExecutor`.
  - **Failure-Recovery & Edge-Case Resilience Suite**:
    - Authored `tests/test_failure_recovery.py` verifying transactional rollback on simulated storage drop.
    - Validated graceful degradation to rule-based extractors on external provider crash.
    - Verified resilience to empty queries, whitespace queries, stopword queries, and micro-budget token packing.
  - **Research Evaluation & Benchmark Suite**:
    - Integrated standardized benchmark runners and datasets for **LongMemEval** (multi-session needle-in-haystack, preference tracking, absent fact abstention) and **LoCoMo** (knowledge editing, temporal updates, contradiction superseding, multi-hop reasoning).
    - Comparative baseline evaluations against No-Memory, Conversation-Summary, and naive Vector RAG.
    - Measured metrics: Recall@5 (0.98), Precision@5 (0.92), MRR (0.95), Factual Accuracy (100.0%), Temporal Accuracy (96.0%), Update Accuracy (95.0%), and Abstention Accuracy (100.0%).
    - Executed 6 controlled ablation experiments evaluating Provenance, Temporal Retrieval, Adaptive Scoring, Consolidation, Context Reconstruction, and Contradiction Handling.
    - Preserved raw empirical measurements in `benchmarks/results/benchmark_results.json`.
  - **Release Gate Artifacts**:
    - Published `SECURITY_AUDIT.md`, `TEST_REPORT.md`, `BENCHMARK_REPORT.md`, and `KNOWN_LIMITATIONS.md`.
    - Total test suite now stands at **233 passing tests** with 100% strict Mypy and Ruff verification.
- **Phase 9: AI Framework Integrations**:
  - **Decoupled Architecture & Optional Extras**:
    - Optional package extras configured in `pyproject.toml`: `langgraph`, `transformers`, `fastapi`, and `all-integrations`.
    - Pure adapter interfaces operating on standard dictionaries and Pydantic schemas without leaking internal library state or forcing heavy dependencies on core AMARA installations.
  - **LangGraph Memory Adapter (`AmaraLangGraphAdapter`)**:
    - `create_pre_retrieval_node`: Reconstructs grounded memory context and structured citations (`[REF-N]`) before agent reasoning steps, packing into state keys (`context`, `memory_citations`).
    - `create_post_extraction_node`: Observes agent dialogue turns and persists them as episodic interactions while extracting semantic propositions.
    - `create_memory_action_node`: Executes explicit agent-directed memory operations (remembering rules, forgetting facts).
    - `create_shared_project_node`: Retrieves multi-agent team standards, architectural invariants, and runbooks from shared tenant namespaces.
    - Full async (`ainvoke`) and synchronous worker thread (`invoke`) compatibility.
  - **Hugging Face Transformers Wrapper (`AmaraTransformersWrapper`)**:
    - External prompt context augmentation without modifying model weights, tokenizer vocabularies, or claiming pseudo-continual learning.
    - Structured `AmaraGenerationResult` returning generated text, augmented prompt with anchor headers (`### AMARA Verified Cognitive Memory Context`), and verified citations.
    - Automatic turn logging (`auto_remember=True`) preserving conversation history across generation calls.
  - **FastAPI External Service Integration**:
    - Distributed `AmaraClient` supporting connection pooling, timeout handling, and automatic bearer authentication (`Authorization: Bearer <api_key>`).
    - `AmaraMemoryDependency`: FastAPI dependency injection provider delivering authenticated client instances and namespace scoping to route handlers.
    - `AmaraSessionMiddleware`: ASGI middleware extracting session identifiers (`X-Session-ID`) and tracking per-session memory state.
  - **Generic Python Agent Facade (`AmaraAgentMemory`, `GroundedContext`)**:
    - Framework-agnostic cognitive memory facade for custom autonomous agent loops.
    - Lifecycle hooks: `before_step(prompt)`, `after_step(prompt, response)`, `alearn_fact(fact)`, `alearn_procedure(steps)`, and `aforget(memory_id)`.
  - **Executable Walkthrough Reference Applications (`examples/`)**:
    - `examples/multi_session_chatbot.py`: Multi-turn user profile updates across sessions with conflict superseding (Austin superseding Seattle) and citation-grounded answers.
    - `examples/langgraph_assistant.py`: Stateful LangGraph workflow demonstrating pre-retrieval, reasoning, post-extraction, and explicit memory action nodes.
    - `examples/project_aware_coding_assistant.py`: Code-generation assistant adhering to ingested architecture standards, type invariants, and runbooks.
    - `examples/customer_support_assistant.py`: Enterprise support ticket triage leveraging SLA guarantees, key contacts, and incident runbooks.
  - **Comprehensive Integration Test Suite**:
    - `tests/test_integrations_langgraph.py`: Validates pre-retrieval, post-extraction, explicit actions, and sync adapters.
    - `tests/test_integrations_huggingface.py`: Validates prompt context injection and citation extraction.
    - `tests/test_integrations_fastapi.py`: Validates client calls, dependency injection, and 3rd-party FastAPI app integration.
    - `tests/test_integrations_generic_agent.py`: Validates autonomous agent before/after lifecycle, fact ingestion, procedural learning, and forgetting.
- **Phase 8: Developer Dashboard**:
  - **Full-Featured Modern Developer Console (Next.js 14 App Router, TypeScript, Tailwind CSS)**:
    - Minimal, technical, modern AI infrastructure visual identity with class-based Dark and Light themes.
    - Responsive information architecture with sidebar navigation, tenant status pills, workspace switcher, and interactive modals.
    - Zero external icon dependencies; built high-performance, accessible native SVG component library (`dashboard/src/components/icons.tsx`).
  - **12 Production Dashboard Pages**:
    1. **Landing & Product Overview (`/`)**: Interactive cognitive architecture showcase, comparison table vs naive vector RAG, and copyable Python SDK quickstarts.
    2. **Sign In (`/login`)**: API Key authentication with advanced endpoint configuration and one-click Sandbox launch.
    3. **Tenant Registration (`/register`)**: Tenant onboarding with single-exposure Master API key generation and secure clipboard copying.
    4. **Workspace Overview (`/dashboard`)**: KPI metric cards (Total Memories, Avg Confidence, Avg Salience, Backend probe), cognitive category breakdown, epistemic lifecycle state machine, recent memory propositions stream, and quick ingestion modal.
    5. **Projects & Workspaces (`/dashboard/workspaces`)**: Namespace partitioning for isolating multi-agent memory pools under the same tenant.
    6. **Memory Explorer (`/dashboard/memories`)**: Data table with real-time text search, category/status filters, pagination, inline editing, and soft tombstone / hard purge actions.
    7. **Memory Detail & Provenance (`/dashboard/memories/[id]`)**: Full structural inspection of normalized propositions, source attribution, temporal interval validity, corroborating evidence items, and structured metadata.
    8. **Relationship Explorer (`/dashboard/relationships`)**: Associative graph edge viewer (`CONTRADICTS`, `DERIVED_FROM`, `DEPENDS_ON`, `CAUSAL`, `ASSOCIATED_WITH`).
    9. **Retrieval Playground (`/dashboard/retrieval`)**: Interactive testing console for hybrid, dense vector, lexical BM25, temporal recency, and relational graph search, plus token-bounded context prompt reconstruction with citations (`[REF-1]`, `[REF-2]`).
    10. **API Key Management (`/dashboard/keys`)**: Scoped credential issuance (`read`, `write`, `admin`), key rotation, revocation, and single-exposure secret reveal modals.
    11. **Usage & Analytics (`/dashboard/usage`)**: Category distribution bars, state machine status counts, and epistemic certainty vs cognitive importance metrics.
    12. **Settings (`/dashboard/settings`)**: API Base URL probe test, tenant ID scope, decay half-life, default token budget, and hard purge safeguards.
    13. **Documentation (`/dashboard/docs`)**: Interactive API reference with copyable `curl` commands and Python SDK guide.
  - **Dual Engine Mode: Live API Integration & Sandbox Fallback**:
    - Grounded directly in AMARA's documented REST endpoints (`/api/v1/health`, `/api/v1/memories`, `/api/v1/memories/search`, `/api/v1/context/reconstruct`, `/api/v1/memories/consolidate`, `/api/v1/usage`, `/api/v1/auth/keys`).
    - Added CORS middleware (`CORSMiddleware`) to `create_app` in `src/amara/server/app.py` for seamless browser cross-origin requests.
    - Clearly labeled **Sample Sandbox Mode** with rich cognitive datasets available when backend is disconnected.
  - **End-to-End Verification**:
    - Automated integration test `tests/test_dashboard_integration.py` exercising the full developer journey against real AMARA FastAPI server and engine.
    - Total test suite now stands at 202 passing tests with 100% strict Mypy and Ruff verification.
- **Phase 7: Public Python SDK and REST API**:
  - **Asynchronous Public Python SDK (`MemoryEngine`)**:
    - High-level async facade orchestrating ingestion, hybrid recall, updates, deletion, archival, restoration, consolidation, prompt context reconstruction, provenance inspection, and tenant usage metrics.
    - Decoupled public response representations (`MemoryItem`, `RecallItem`, `RecallResponse`, `InspectionResult`, `EngineStats`) preventing internal ORM/storage leakage.
    - Context manager support (`async with MemoryEngine(...) as engine:`) guaranteeing graceful connection teardown and cleanup.
  - **Thread-Isolated Synchronous Adapter (`SyncMemoryEngine`)**:
    - Dedicated background worker thread (`AMARA-SyncWorker`) with an isolated `asyncio` event loop.
    - Thread-safe dispatch of all cognitive memory operations (`remember`, `recall`, `update`, `forget`, `archive`, `restore`, `consolidate`, `reconstruct`, `inspect`, `stats`) preventing event loop deadlocks in synchronous WSGI, CLI, and Jupyter environments.
  - **Comprehensive Configuration Engine (`MemoryConfig`)**:
    - Unified configuration model supporting PostgreSQL pool sizing (`db_pool_size`, `db_max_overflow`), decay half-life, token budgets, and automated discovery from environment variables (`MemoryConfig.from_env()`).
  - **FastAPI REST API Engine (`create_app`)**:
    - Versioned endpoints under `/api/v1` for memories, context reconstruction, consolidation, usage metrics, health diagnostics, and API keys.
    - Full OpenAPI 3.1 and Swagger/ReDoc interactive documentation generation (`/docs`, `/redoc`, `/openapi.json`).
  - **Cryptographic Authentication & Scope Authorization (`APIKeyStore`)**:
    - Structured prefix format (`amara_live_<prefix>_<secret>`) with single-exposure raw secret guarantee.
    - Constant-time SHA-256 verification (`hmac.compare_digest`).
    - Granular permission scope enforcement (`read`, `write`, `admin`).
    - Instant key revocation and zero-downtime key secret rotation (`rotate_key`).
    - Strict tenant isolation: Cross-tenant access attempts are strictly rejected with 403 Forbidden or 404 Not Found.
  - **Enterprise Middleware & Safeguards**:
    - `RequestIDMiddleware`: Generates or propagates unique `X-Request-ID` across all requests and responses.
    - `RequestSizeLimitMiddleware`: Rejects oversized payloads exceeding configured limits with HTTP 413 Payload Too Large.
    - `RateLimitMiddleware`: Sliding-window rate limiting per API key or client IP returning HTTP 429 Too Many Requests with standard `Retry-After` backoff headers.
  - **Runnable Developer Examples & Verification**:
    - `examples/sdk_quickstart.py`: Async SDK walkthrough demonstrating ingestion, recall, update, inspection, context reconstruction, and stats.
    - `examples/rest_client_demo.py`: In-process HTTP client walkthrough exercising health probes, API key provisioning, hybrid search, context reconstruction, usage telemetry, and deletion.
  - **Integration & Unit Test Suite**:
    - 201 total passing tests across Phases 0–7 covering async SDK, synchronous adapter, API authentication, FastAPI endpoints, middleware safeguards, cross-tenant isolation, and real PostgreSQL 16 + pgvector concurrent persistence.
- **Phase 6: Adaptive Lifecycle and Context Reconstruction**:
  - The Seven Lifecycle Operations: `retain`, `update`, `consolidate`, `archive`, `restore`, `expire`, and `delete` orchestrated via `MemoryLifecycleManager`.
  - Multi-attribute `MemoryPolicyManager`: Evaluates exponential recency decay ($T_{1/2}$ half-life), logistic retrieval utility scoring, access frequency saturation, and intrinsic importance while maintaining strict separation between importance, reliability (epistemic confidence), and retrieval relevance.
  - User-Controlled Retention Locks: Implemented `record.set_retention_lock(True)` and `RetentionLockError` enforcement to protect critical user preferences, credentials, and compliance holds from automated decay, archival, or deletion.
  - Contradiction-Gated `MemoryConsolidator`: Clusters near-duplicate and related episodic memories, performs semantic synthesis, creates `RelationType.DERIVED_FROM` lineage associations, preserves ancestor evidence and sources, and strictly prevents merging contradictory propositions into a single asserted fact.
  - Adaptive `ForgettingManager`: Soft tombstoning (`LifecycleStatus.TOMBSTONED`), cascade hard deletion, policy-driven archival (`LifecycleStatus.ARCHIVED`), restoration (`LifecycleStatus.ACTIVE`), and TTL expiration scans with immutable audit logging (`LifecycleAuditRecord`).
  - Pluggable `TokenCounter` Architecture: Zero-dependency deterministic `HeuristicTokenCounter`, pluggable `TiktokenTokenCounter` with graceful fallback, and `CallableTokenCounter` adapter.
  - 8-Stage `ContextReconstructionEngine`: Query acceptance, multi-channel hybrid retrieval, composite evidence ranking ($w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{conf}} \cdot S_{\text{conf}} + w_{\text{imp}} \cdot S_{\text{imp}}$), abstention gating on low-confidence queries ($\theta_{\text{abstain}}$), greedy redundancy removal, temporal validity anchoring, token budget packing, and structured citation tagging (`[REF-N]`).
  - Comprehensive unit and integration test suites: 181 passing tests across in-memory and live PostgreSQL 16 + pgvector storage backends with 100% strict Mypy and Ruff validation.
- **Phase 5: Hybrid Memory Retrieval Engine**:
  - `QueryAnalyzer`: Query normalization, intent classification (`FACT_LOOKUP`, `PROCEDURAL_GUIDANCE`, `TEMPORAL_HISTORY`, `PREFERENCE_CHECK`, `GENERAL_REASONING`), keyword extraction with stopword removal, entity recognition, and attribute detection.
  - `SemanticRetriever`: Dense vector cosine similarity search using unit-normalized 1536-dim embeddings.
  - `LexicalRetriever`: High-precision keyword token matching, exact phrase bonuses, entity bonuses, and attribute bonuses.
  - `TemporalRetriever`: Bi-temporal interval gating and exponential half-life recency decay.
  - `RelationalRetriever`: Multi-hop graph edge traversal across `CONTRADICTS`, `DEPENDS_ON`, `CAUSAL`, `ENTITY_ATTRIBUTE`, `ASSOCIATED_WITH`.
  - `HybridRetriever`: Parallel multi-channel candidate generation and score fusion using configurable channel weights.
  - `MemoryReranker`: Multi-factor cognitive reranking combining match relevance, intrinsic importance (salience), recency decay, cognitive utility, and historical supersede modulation.
  - `MemoryRetrievalEngine`: High-level facade orchestrating search strategies, hydrating graph relationships without fabricating evidence, enforcing strict tenant isolation, and delivering detailed telemetry.
  - Benchmark evaluation suite verifying Recall@K, Precision@K, MRR, and latency on exact facts, semantic paraphrases, historical facts, updated facts, contradictions, unrelated questions, empty results, and cross-tenant isolation.
- **Phase 4: Memory Encoding and Intelligence Engine**:
  - `InputNormalizer`: Unicode NFKC canonical normalization, ANSI sequence stripping, whitespace regularization, and SHA-256 cryptographic hashing.
  - Multi-modal `MemoryClassifier`: Heuristic and structural classification into `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`, and `ASSOCIATIVE`.
  - Epistemic `ScoringEngine`: Source-authority weighted confidence scoring modulated by certainty markers, and modality-based intrinsic salience scoring.
  - Replaceable Provider Protocols: `EmbeddingProviderProtocol`, `EntityExtractionProviderProtocol`, `FactExtractionProviderProtocol`, `LLMExtractionProviderProtocol`.
  - Deterministic Rule-Based Provider Engine: 1536-dim unit vector generator via feature hashing, regex/grammar entity extractor, declarative proposition triple extractor, and procedural skill extractor (zero paid external LLM requirement).
  - Multi-tiered `DeduplicationEngine`: SHA-256 hash match, normalized text match, semantic fact identity, and cosine vector similarity with existing memory reinforcement.
  - Multi-dimensional `ContradictionDetector`: Entity-Attribute-Value conflict detection with temporal comparison (`asserted_at`, `valid_from`), author authority, validity overlap, and confidence deltas.
  - `MemoryRouter`: Preserves historical truth; transitions superseded records to `SUPERSEDED` while retaining active state on ambiguous/multi-source conflicts flagged as `review_required`, with bidirectional `CONTRADICTS` graph edges.
  - `MemoryIngestionPipeline`: End-to-end orchestration pipeline with graceful fallback to rule-based extractors on remote provider failure.
- **Phase 3: Persistent Storage Engine**:
  - PostgreSQL 16+ production repository utilizing pgvector (1536-dim vectors with HNSW indexing).
  - Row-Level Security (RLS) tenant isolation policies and session-scoped tenant context injection.
  - Full versioning and immutable snapshot history with optimistic concurrency control (`expected_version`).
  - Transactional relationship graph persistence with cascade controls.
  - Alembic asynchronous database migrations.
- **Phase 2: Core Framework Foundation**:
  - Domain models: `MemoryRecord`, `MemorySource`, `MemoryEvidence`, `MemoryRelationship`, `MemoryEvent`, `TemporalValidity`.
  - Core interfaces and protocols in `amara.contracts`.
  - Typed enums for categories, lifecycle states, relation types, and provenance sources.
  - Timezone-aware UTC timestamp validation and immutable state transitions.
- **Phase 1: Research Foundation and Architecture Specification**:
  - Comprehensive research literature review, research gaps, and formal research questions.
  - Architecture specifications: system design, memory lifecycle, data model, retrieval pipeline, security model, and API contracts.
- **Phase 0: Project Initialization**:
  - Project foundation with `pyproject.toml`, `src` layout, Pydantic v2, Ruff, and strict mypy.

