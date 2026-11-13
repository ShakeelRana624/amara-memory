# AMARA PostgreSQL Storage Engine & Migration Architecture

## 1. Overview & Architecture Objectives

AMARA (Adaptive Memory Architecture for Reasoning and AI) requires a robust, industrial-grade persistence layer that unifies high-dimensional vector search, structured relational knowledge graphs, bitemporal validity querying, and audit history tracking.

The storage subsystem fulfills the following core architectural requirements:

1. **Vendor & Framework Independence**: Domain models and storage contracts remain completely decoupled from FastAPI, LangChain, LangGraph, and specific external LLM providers.
2. **Production Storage Stack**: Built upon **PostgreSQL 16+**, **pgvector 0.6+**, **SQLAlchemy 2.x Async**, **asyncpg**, and **Alembic**. No in-memory mocks are used in production configurations.
3. **Optimistic Concurrency Control (OCC)**: Guarantees transaction-safe concurrent updates without silent data overwrites or lost updates.
4. **Defense-in-Depth Tenant Isolation**: Combines strict application-level query scoping with PostgreSQL native **Row-Level Security (RLS)**.
5. **Comprehensive Lineage & Auditability**: Preserves past record versions in dedicated audit history tables and emits append-only domain events for all state changes.

---

## 2. Relational Schema Specification

The storage schema consists of four primary relational tables and two PostgreSQL extensions.

```mermaid
erDiagram
    memory_records ||--o{ memory_relationships : "source_id / target_id"
    memory_records ||--o{ memory_version_history : "memory_id"
    memory_records ||--o{ memory_events : "memory_id"

    memory_records {
        uuid id PK
        string tenant_id
        string namespace
        string memory_type
        string status
        text original_content
        text normalized_content
        string source_id
        string source_type
        string author_id
        string session_id
        string source_event_id
        string content_hash
        string extractor_signature
        jsonb source_metadata
        float confidence
        float importance
        timestamp_tz asserted_at
        timestamp_tz valid_from
        timestamp_tz valid_to
        int version
        uuid root_id
        uuid_array parent_ids
        vector_1536 embedding
        string embedding_model_id
        jsonb metadata
        jsonb evidence
        int access_count
        float utility_score
        timestamp_tz last_accessed_at
        timestamp_tz created_at
        timestamp_tz updated_at
        timestamp_tz deleted_at
    }

    memory_relationships {
        uuid relationship_id PK
        string tenant_id
        uuid source_id FK
        uuid target_id FK
        string relation_type
        float weight
        boolean bidirectional
        jsonb metadata
        timestamp_tz created_at
    }

    memory_version_history {
        uuid history_id PK
        uuid memory_id FK
        string tenant_id
        int version
        text original_content
        text normalized_content
        string status
        jsonb metadata
        timestamp_tz changed_at
        string changed_by
        string change_reason
    }

    memory_events {
        uuid event_id PK
        string tenant_id
        string namespace
        uuid memory_id
        string event_type
        timestamp_tz timestamp
        jsonb payload
    }
```

### 2.1 `memory_records` Table

The central table storing all cognitive memory modalities (episodic, semantic, procedural, associative).

| Column Name | SQL Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | Primary Key | Globally unique memory record identifier |
| `tenant_id` | `VARCHAR(128)` | No | - | Multi-tenant partition scope |
| `namespace` | `VARCHAR(128)` | No | `'default'` | Logical domain or agent namespace |
| `memory_type` | `VARCHAR(32)` | No | - | Modality: `working`, `episodic`, `semantic`, `procedural`, `associative` |
| `status` | `VARCHAR(32)` | No | `'active'` | Lifecycle status: `active`, `decaying`, `consolidated`, `superseded`, `archived`, `tombstoned` |
| `original_content` | `TEXT` | No | - | Verbatim memory text content |
| `normalized_content` | `TEXT` | No | - | Normalized lowercased representation for lexical search |
| `source_id` | `VARCHAR(128)` | No | - | Identifier of the originating source document or session |
| `source_type` | `VARCHAR(64)` | No | - | Origin category: `user_input`, `agent_reasoning`, `tool_execution`, etc. |
| `author_id` | `VARCHAR(128)` | No | - | Creator identity (user ID, agent ID, tool identifier) |
| `session_id` | `VARCHAR(128)` | Yes | `NULL` | Conversation session context pointer |
| `source_event_id` | `VARCHAR(128)` | Yes | `NULL` | Upstream telemetry event identifier |
| `content_hash` | `VARCHAR(64)` | No | - | SHA-256 cryptographic hash of ingested content |
| `extractor_signature`| `VARCHAR(128)` | Yes | `NULL` | Model or rule identifier that derived this memory |
| `source_metadata` | `JSONB` | No | `'{}'` | Raw provenance metadata |
| `confidence` | `FLOAT` | No | `1.0` | Epistemic certainty score `[0.0, 1.0]` |
| `importance` | `FLOAT` | No | `0.5` | Cognitive salience score `[0.0, 1.0]` |
| `asserted_at` | `TIMESTAMPTZ` | No | - | Timestamp when fact was stated in reality |
| `valid_from` | `TIMESTAMPTZ` | No | - | Bitemporal validity window start |
| `valid_to` | `TIMESTAMPTZ` | Yes | `NULL` | Bitemporal validity window end (NULL = indefinitely valid) |
| `version` | `INTEGER` | No | `1` | Monotonically increasing version counter for OCC |
| `root_id` | `UUID` | No | - | Root ancestor memory ID in derivation tree |
| `parent_ids` | `UUID[]` | No | `'{}'` | Immediate parent memory IDs |
| `embedding` | `vector(1536)` | Yes | `NULL` | Dense embedding vector representation |
| `embedding_model_id`| `VARCHAR(128)` | Yes | `NULL` | Model ID that produced the embedding vector |
| `metadata` | `JSONB` | No | `'{}'` | Modality-specific attributes and domain tags |
| `evidence` | `JSONB` | No | `'[]'` | Serialized corroborating evidence list |
| `access_count` | `INTEGER` | No | `0` | Number of times retrieved into context |
| `utility_score` | `FLOAT` | No | `0.0` | Accumulated reinforcement feedback |
| `last_accessed_at` | `TIMESTAMPTZ` | Yes | `NULL` | Last retrieval timestamp |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Ingestion timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | Last mutation timestamp |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Soft deletion tombstone timestamp |

---

### 2.2 `memory_relationships` Table

Represents directed and bidirectional typed relational edges between memory nodes in the associative memory graph.

| Column Name | SQL Type | Nullable | Default | Description |
|---|---|---|---|---|
| `relationship_id` | `UUID` | No | Primary Key | Relational edge identifier |
| `tenant_id` | `VARCHAR(128)` | No | - | Multi-tenant scope |
| `source_id` | `UUID` | No | FK (`memory_records.id`) | Origin memory node (CASCADE delete) |
| `target_id` | `UUID` | No | FK (`memory_records.id`) | Destination memory node (CASCADE delete) |
| `relation_type` | `VARCHAR(64)` | No | - | `causal`, `temporal_next`, `entity_attr`, `contradicts`, `depends_on`, `associated_with` |
| `weight` | `FLOAT` | No | `1.0` | Edge strength `[0.0, 1.0]` |
| `bidirectional` | `BOOLEAN` | No | `false` | Whether edge is traversable in both directions |
| `metadata` | `JSONB` | No | `'{}'` | Relational attributes |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | Relationship creation timestamp |

---

### 2.3 `memory_version_history` Table

Immutable audit trail capturing previous states of memory records prior to mutation.

| Column Name | SQL Type | Nullable | Default | Description |
|---|---|---|---|---|
| `history_id` | `UUID` | No | Primary Key | History snapshot identifier |
| `memory_id` | `UUID` | No | FK (`memory_records.id`) | Associated memory record (CASCADE delete) |
| `tenant_id` | `VARCHAR(128)` | No | - | Multi-tenant partition |
| `version` | `INTEGER` | No | - | Historical version number |
| `original_content` | `TEXT` | No | - | Historical content |
| `normalized_content`| `TEXT` | No | - | Historical normalized content |
| `status` | `VARCHAR(32)` | No | - | Historical lifecycle status |
| `metadata` | `JSONB` | No | `'{}'` | Historical metadata snapshot |
| `changed_at` | `TIMESTAMPTZ` | No | `now()` | Timestamp of modification |
| `changed_by` | `VARCHAR(128)` | No | - | Actor or subsystem that initiated change |
| `change_reason` | `VARCHAR(256)` | Yes | `NULL` | Explicit reason or audit comment |

---

### 2.4 `memory_events` Table

Domain event stream for reactive agents and external audit logging.

| Column Name | SQL Type | Nullable | Default | Description |
|---|---|---|---|---|
| `event_id` | `UUID` | No | Primary Key | Event identifier |
| `tenant_id` | `VARCHAR(128)` | No | - | Tenant scope |
| `namespace` | `VARCHAR(128)` | No | - | Partition namespace |
| `memory_id` | `UUID` | No | - | Target memory record ID |
| `event_type` | `VARCHAR(64)` | No | - | `memory.created`, `memory.updated`, `memory.tombstoned`, `memory.purged` |
| `timestamp` | `TIMESTAMPTZ` | No | `now()` | Event occurrence time |
| `payload` | `JSONB` | No | `'{}'` | Event specific attributes and state diffs |

---

## 3. Indexing Strategy & Performance Architecture

AMARA utilizes specialized indexing mechanisms tailored for hybrid search, temporal reasoning, and high-concurrency multi-tenant filtering.

### 3.1 pgvector HNSW Index (Dense Vector Search)

Vector proximity search is accelerated using Hierarchical Navigable Small World (HNSW) graph indexing with cosine distance:

```sql
CREATE INDEX idx_memory_embedding_hnsw ON memory_records 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

- **`vector_cosine_ops`**: Uses `<=>` cosine distance, ideal for normalized text embedding models.
- **`m = 16`**: Maximum number of bidirectional connections per element in the graph layer, balancing memory usage and recall.
- **`ef_construction = 64`**: Exploration factor during graph build, ensuring high search accuracy.

### 3.2 B-Tree Indexes (Relational & Temporal Filtering)

- **`idx_memory_tenant_modality`**: `(tenant_id, namespace, memory_type, status)` optimizes multi-attribute filtering for active memory recall.
- **`idx_memory_temporal`**: `(tenant_id, valid_from, valid_to)` accelerates bitemporal point-in-time point queries (`valid_from <= :t AND (valid_to IS NULL OR valid_to > :t)`).
- **`idx_rel_tenant_source` / `idx_rel_tenant_target`**: `(tenant_id, source_id, relation_type)` and `(tenant_id, target_id, relation_type)` enable sub-millisecond bidirectional graph traversal.
- **`idx_history_tenant_memory_version`**: `(tenant_id, memory_id, version)` allows chronological retrieval of past audit revisions.

### 3.3 GIN Index (JSONB Metadata Containment)

- **`idx_memory_metadata_gin`**: `USING gin (metadata)` enables arbitrary nested key-value queries using PostgreSQL's JSONB containment operator `@>`:

```sql
SELECT * FROM memory_records 
WHERE tenant_id = 'tenant-1' 
  AND metadata @> '{"domain": {"security": "critical"}}';
```

---

## 4. Concurrency Control & State Management

### 4.1 Optimistic Concurrency Control (OCC)

To prevent race conditions during concurrent agent interactions, AMARA employs atomic conditional updates:

```sql
UPDATE memory_records
SET version = :new_version,
    original_content = :content,
    normalized_content = :normalized,
    status = :status,
    metadata = :metadata,
    updated_at = :now
WHERE id = :memory_id
  AND tenant_id = :tenant_id
  AND version = :expected_version;
```

If another process has mutated the memory in the interim, `rowcount` returns `0`, causing `PostgresMemoryRepository` to immediately raise `InvalidMemoryStateError` without committing changes.

### 4.2 Version Snapshot Workflow

Every successful update executes within an atomic transaction that:
1. Validates the lifecycle state machine transition (`LEGAL_TRANSITIONS`).
2. Inserts a snapshot of the current state into `memory_version_history`.
3. Applies the update and increments `version = version + 1`.
4. Emits a `MemoryEventType.UPDATED` entry into `memory_events`.

---

## 5. Security & Multi-Tenant Isolation

### 5.1 Defense-in-Depth Architecture

Isolation is enforced at two distinct architectural tiers:

1. **Application Layer**: Every query generated by `PostgresMemoryRepository` mandates a sanitized `tenant_id` equality predicate.
2. **Database Engine Layer (Row-Level Security)**: Tables have PostgreSQL Row-Level Security enabled:

```sql
ALTER TABLE memory_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_records ON memory_records
FOR ALL USING (
  tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')
  OR current_setting('app.bypass_rls', true) = 'on'
);
```

### 5.2 Transactional Session Parameter Injection

When an application session opens via `DatabaseManager.session(tenant_id=...)`, the tenant context is set locally using parameterized SQL:

```python
await session.execute(
    text("SELECT set_config('app.current_tenant_id', :tid, true);"),
    {"tid": clean_tenant},
)
```

The third argument (`true`) binds the setting strictly to the current transaction. Once the transaction commits or rolls back, the setting automatically reverts, preventing cross-tenant leakage across pooled database connections.

---

## 6. Deletion Lifecycle & Cascade Guarantees

AMARA supports two distinct deletion semantics:

### 6.1 Soft Deletion (Tombstone)
- Marks `status = 'tombstoned'` and records `deleted_at = now()`.
- Default queries (`list_memories`, `query`) automatically filter out tombstoned records unless explicitly requested.
- Emits `MemoryEventType.TOMBSTONED`.

### 6.2 Hard Cascade Deletion (Purge)
When `delete_memory(tenant_id, memory_id, hard=True, cascade=True)` is called:
- **Foreign Keys**: Associated rows in `memory_relationships` and `memory_version_history` are automatically deleted via `ON DELETE CASCADE`.
- **Derivation Graph Pruning**: 
  - Derived memories derived solely from the purged record (orphans) are recursively purged.
  - Multi-parent derived memories have the purged ID removed from their `parent_ids` array, remaining intact with their surviving ancestry.
- Emits `MemoryEventType.PURGED` with total count of purged records.

---

## 7. Migration Runbook & Alembic Workflow

Alembic manages all schema revisions using an asynchronous connection pattern.

### 7.1 Configuration Files
- `alembic.ini`: Root configuration specifying script location (`migrations`), template, and UTC timezone.
- `migrations/env.py`: Asynchronous runner that imports `Base.metadata` from `src.amara.storage.schema` and executes migrations via `AsyncEngine`.
- `migrations/versions/0001_initial_amara_schema.py`: Initial migration script creating extensions, tables, indexes, and RLS policies.

### 7.2 Executing Migrations

**Apply Latest Schema Upgrades:**
```bash
alembic upgrade head
```

**Rollback Schema to Base:**
```bash
alembic downgrade base
```

**Generate a New Migration Autocommit Revision:**
```bash
alembic revision -m "add_cognitive_modality_column"
```

### 7.3 Operational Runbook Checklist

1. **Pre-flight Connectivity**: Ensure PostgreSQL 16+ is running and the user has permissions to create extensions `vector` and `uuid-ossp`.
2. **Environment Variable**: Set `AMARA_DATABASE_URL` in the environment or `.env`:
   ```bash
   AMARA_DATABASE_URL=postgresql+asyncpg://amara:password@localhost:5432/amara_db
   ```
3. **Automated Verification**: Run the integration test suite to verify end-to-end migration lifecycle and CRUD operations:
   ```bash
   pytest tests/test_postgres_storage.py
   ```
