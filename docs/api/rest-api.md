# AMARA REST API Specification

The AMARA REST API provides high-performance, versioned HTTP endpoints for cognitive memory ingestion, hybrid retrieval, lifecycle management, and prompt context reconstruction.

Built on **FastAPI** and **Starlette**, it offers complete OpenAPI documentation (`/docs` and `/redoc`), cryptographic API key authentication, tenant isolation, request tracing, payload size limits, and sliding-window rate limiting.

---

## 1. Authentication & Security Model

### API Key Format
API keys follow the structured prefix pattern:
```
amara_live_{prefix}_{secret}
```
- `amara_live_`: Constant service identifier.
- `{prefix}`: 8-character hexadecimal string used for indexed, constant-time database lookup.
- `{secret}`: 48-character high-entropy hexadecimal string (192+ bits of cryptographic entropy).

### Single-Exposure Guarantee
The raw secret is **never stored** in plaintext. When an API key is generated or rotated, the raw key is returned in the HTTP response **exactly once**. In persistence, only the cryptographic SHA-256 hash is retained (`hmac.compare_digest` constant-time verification).

### Header Convention
Clients authenticate requests using either:
```http
Authorization: Bearer amara_live_a1b2c3d4_...
```
or
```http
X-API-Key: amara_live_a1b2c3d4_...
```

### Permission Scopes

| Scope | Allowed Operations |
|---|---|
| `read` | Retrieve memories, search, inspect provenance, reconstruct context, view usage metrics. |
| `write` | Ingest new memories, update content/metadata, soft tombstone, trigger consolidation. |
| `admin` | Issue new API keys, rotate keys, revoke keys, permanently purge memories, bypass all sub-scopes. |

### Strict Tenant Boundary
Every API key is bound to an immutable `tenant_id`. Any attempt to access, search, update, or delete records belonging to another tenant is blocked with **403 Forbidden** or **404 Not Found**.

---

## 2. Global Middleware & Diagnostic Headers

Every HTTP response returned by the AMARA server includes:
- `X-Request-ID`: Unique tracing identifier (`req_...`). If the client passes an `X-Request-ID` in the request header, it is echoed back for distributed tracing.
- `Retry-After`: Included on **429 Too Many Requests** responses indicating the number of seconds to back off before retrying.

### Safeguards

| Middleware | Trigger Condition | Status Code | Error Code |
|---|---|---|---|
| Payload Size Limit | `Content-Length > max_request_bytes` (default 1 MB) | `413 Payload Too Large` | `PAYLOAD_TOO_LARGE` |
| Sliding-Window Rate Limiter | Exceeded requests per minute per API key / IP | `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` |
| Request Validation | Malformed JSON or schema constraint violation | `422 Unprocessable Content` | `VALIDATION_ERROR` |

---

## 3. Endpoints Reference

### Health & Diagnostics

#### `GET /api/v1/health`
Unauthenticated health and diagnostic probe. Returns service readiness, framework version, and active persistence engine connectivity.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "storage_backend": "postgres",
  "database_connected": true,
  "timestamp": "2026-11-13T10:50:00Z"
}
```

---

### Authentication & Key Management

#### `POST /api/v1/auth/keys`
Issue a new scoped API key for the caller's tenant. Requires `admin` scope.

**Request**:
```json
{
  "name": "Customer Support Agent Key",
  "workspace_id": "support",
  "scopes": ["read", "write"],
  "expires_in_days": 90.0
}
```

**Response `201 Created`**:
```json
{
  "key_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Customer Support Agent Key",
  "key_prefix": "90d49de2",
  "raw_key": "amara_live_90d49de2_8f14e4b... (only shown once)",
  "scopes": ["read", "write"],
  "tenant_id": "tenant_acme",
  "created_at": "2026-11-13T10:50:00Z",
  "expires_at": "2027-02-11T10:50:00Z"
}
```

#### `GET /api/v1/auth/keys`
List active and revoked API keys for the caller's tenant (raw secrets are never returned). Requires `admin` scope.

#### `DELETE /api/v1/auth/keys/{key_id}`
Immediately revoke an API key. Requires `admin` scope.

#### `POST /api/v1/auth/keys/{key_id}/rotate`
Rotate an API key's secret, immediately invalidating the old credential while preserving permission scopes and metadata. Requires `admin` scope.

---

### Memory CRUD & Ingestion

#### `POST /api/v1/memories`
Ingest, normalize, extract, deduplicate, and persist a new cognitive proposition. Requires `write` scope.

**Request**:
```json
{
  "content": "User prefers PostgreSQL with pgvector for vector storage.",
  "author_id": "developer_agent",
  "memory_type": "semantic",
  "confidence": 0.95,
  "importance": 0.8,
  "namespace": "default",
  "metadata": {"preferred_db": "postgresql"}
}
```

**Response `201 Created`**:
```json
{
  "data": {
    "id": "e190689b-a736-404a-83d9-4ea700dfe888",
    "tenant_id": "tenant_acme",
    "namespace": "default",
    "content": "User prefers PostgreSQL with pgvector for vector storage.",
    "normalized_content": "user prefers postgresql with pgvector for vector storage.",
    "memory_type": "semantic",
    "status": "active",
    "confidence": 0.95,
    "importance": 0.8,
    "source_id": "src_4f1b82a",
    "author_id": "developer_agent",
    "version": 1,
    "created_at": "2026-11-13T10:50:00Z",
    "updated_at": "2026-11-13T10:50:00Z",
    "metadata": {"preferred_db": "postgresql"}
  }
}
```

#### `GET /api/v1/memories/{memory_id}`
Retrieve a specific memory item by primary key within caller's tenant boundary. Requires `read` scope.

#### `PATCH /api/v1/memories/{memory_id}`
Perform a controlled update of a memory record's content or metadata tags. Requires `write` scope.

**Request**:
```json
{
  "content": "User prefers PostgreSQL 16+ with pgvector and HNSW index.",
  "metadata": {"index_type": "hnsw"}
}
```

#### `DELETE /api/v1/memories/{memory_id}`
Delete a memory record using soft tombstone or physical purge. Requires `write` scope.

**Query Parameters**:
- `hard` (`bool`, default `false`): If true, permanently purges the record from storage.
- `cascade` (`bool`, default `false`): If true, recursively deletes derived child records.
- `force` (`bool`, default `false`): If true, overrides retention locks when authorized.

---

### Multi-Channel Hybrid Search

#### `POST /api/v1/memories/search`
Execute hybrid vector, lexical, temporal, and relational search across cognitive memories. Requires `read` scope.

**Request**:
```json
{
  "query": "vector database preference",
  "strategy": "hybrid",
  "top_k": 5,
  "namespace": "default",
  "include_historical": false
}
```

**Response `200 OK`**:
```json
{
  "query": "vector database preference",
  "tenant_id": "tenant_acme",
  "namespace": "default",
  "results": [
    {
      "item": {
        "id": "e190689b-a736-404a-83d9-4ea700dfe888",
        "content": "User prefers PostgreSQL with pgvector for vector storage.",
        "memory_type": "semantic",
        "confidence": 0.95
      },
      "relevance_score": 0.9124,
      "confidence": 0.95,
      "match_explanation": "Dense vector cosine similarity match (0.912)"
    }
  ],
  "total_candidates": 1,
  "latency_ms": 7.84
}
```

---

### Grounded Context Reconstruction

#### `POST /api/v1/context/reconstruct`
Reconstruct an 8-stage token-bounded, citation-stamped context prompt block for LLM prompt augmentation. Requires `read` scope.

**Request**:
```json
{
  "query": "Which database does the user prefer?",
  "budget_tokens": 500,
  "strategy": "hybrid"
}
```

**Response `200 OK`**:
```json
{
  "query": "Which database does the user prefer?",
  "formatted_context": "### AMARA Verified Cognitive Memory Context\n\n[REF-1] (Semantic | Conf: 0.95 | Valid: [2026-11-13 to Present])\nUser prefers PostgreSQL with pgvector for vector storage.\n\nCitations:\n  [REF-1] -> Memory e190689b-a736-404a-83d9-4ea700dfe888 (Author: developer_agent)",
  "citations": [
    {
      "citation_tag": "REF-1",
      "memory_id": "e190689b-a736-404a-83d9-4ea700dfe888",
      "source_id": "src_4f1b82a",
      "author_id": "developer_agent",
      "confidence": 0.95,
      "importance": 0.8,
      "temporal_anchor": "2026-11-13 10:50 UTC",
      "snippet": "User prefers PostgreSQL with pgvector for vector storage."
    }
  ],
  "total_tokens_used": 68,
  "remaining_token_budget": 432,
  "abstention_recommended": false,
  "abstention_reason": null,
  "candidates_retrieved": 1,
  "candidates_packed": 1
}
```

---

### Consolidation & Telemetry

#### `POST /api/v1/memories/consolidate`
Trigger episodic-to-semantic consolidation across experience clusters. Requires `write` scope.

#### `GET /api/v1/usage`
Retrieve memory category distribution, lifecycle counts, and average confidence scores for the authenticated tenant. Requires `read` scope.

**Response `200 OK`**:
```json
{
  "tenant_id": "tenant_acme",
  "namespace": null,
  "total_memories": 42,
  "by_category": {
    "semantic": 28,
    "episodic": 14
  },
  "by_status": {
    "active": 40,
    "archived": 2
  },
  "average_confidence": 0.924,
  "average_importance": 0.781
}
```

---

## 4. Structured Error Envelope

All API errors return a standard JSON envelope with `X-Request-ID`:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload format or parameters.",
    "request_id": "req_a1b2c3d4e5f60718",
    "details": [
      {
        "loc": ["body", "content"],
        "msg": "Field required",
        "type": "missing"
      }
    ]
  }
}
```
