# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

