# AMARA Cloud Hosted Platform Launch Verification Runbook

This runbook documents the end-to-end verification protocols for the AMARA hosted cloud service and multi-tenant SaaS environment.

---

## 1. Authentication & Onboarding Verification

| Test Scenario | Verification Protocol | Expected Behavior | Verification Status |
| :--- | :--- | :--- | :--- |
| **New User Registration** | Submit registration form with valid email and password (`/register`). | Creates user tenant record, hashes password, outputs new cryptographic API key. | **VERIFIED** |
| **User Login** | Submit credentials or API key (`/login`). | Generates session JWT/cookie, authorizes access to Dashboard. | **VERIFIED** |
| **Workspace Creation** | Create workspace `customer_support` under tenant. | Allocates isolated memory partition with zero cross-workspace bleed. | **VERIFIED** |
| **API Key Provisioning** | Generate API key with scopes `["read", "write"]`. | Displays `amara_live_...` token once; stores only salted SHA-256 hash. | **VERIFIED** |
| **Key Instant Revocation** | Revoke key via Dashboard or `DELETE /api/v1/keys/{id}`. | Subsequent API calls using key fail immediately with HTTP 401. | **VERIFIED** |

---

## 2. Real-Time API & Memory Operations Verification

| Operation | Test Execution | Verification Output | Status |
| :--- | :--- | :--- | :--- |
| **Ingestion** | `POST /api/v1/memories` with proposition. | Returns HTTP 201 with UUID, extracted facts, and importance $> 0.5$. | **VERIFIED** |
| **Hybrid Recall** | `POST /api/v1/memories/search` with strategy `hybrid`. | Returns ranked candidates with RRF scores and source citations. | **VERIFIED** |
| **Context Reconstruction**| `POST /api/v1/context/reconstruct` with token budget 600. | Returns markdown-formatted context within budget with `[REF-1]` tags. | **VERIFIED** |
| **Consolidation** | `POST /api/v1/memories/consolidate`. | Synthesizes cluster of near-duplicates into unified semantic record. | **VERIFIED** |
| **Deletion / Purge** | `DELETE /api/v1/memories/{id}`. | Soft-deletes record (or purges if outside legal retention hold). | **VERIFIED** |

---

## 3. Hosted Dashboard Experience Verification

Verify that all 13 interactive portal modules function seamlessly in production:
1. **Overview Dashboard** (`/dashboard`): Displays live memory type counts, operation velocity, and health status.
2. **Workspaces View** (`/dashboard/workspaces`): Partitions project memories with custom retention parameters.
3. **Memory Explorer** (`/dashboard/memories`): Real-time search, filters by status (`ACTIVE`, `DECAYING`, `ARCHIVED`), and pagination.
4. **Memory Detail & Provenance** (`/dashboard/memories/[id]`): Displays raw payload, extracted facts, entity graph links, and validity timestamps.
5. **Relationship Graph** (`/dashboard/relationships`): Interactive SVG/Canvas graph showing associative memory connections.
6. **Retrieval Playground** (`/dashboard/retrieval`): Interactive query bar comparing semantic vs. lexical vs. hybrid recall scores.
7. **Integrations Hub** (`/dashboard/integrations`): Ready-to-copy code adapters for LangGraph, Transformers, and FastAPI.
8. **API Key Management** (`/dashboard/keys`): Live generation, rotation, and revocation controls.
9. **Usage & Analytics** (`/dashboard/usage`): Real-time token consumption and request charts.
10. **Platform Settings** (`/dashboard/settings`): Configures decay half-life, default namespaces, and retention locks.
11. **Developer Documentation** (`/dashboard/docs`): Built-in quickstart guides and interactive curl generators.

---

## 4. Multi-Tenant Security & Isolation Verification

- **Cross-Tenant Attack Simulation**: An authenticated API key from `tenant_alpha` attempting to retrieve or update a memory belonging to `tenant_beta` yields HTTP 404 (or HTTP 403 on administration endpoints).
- **SQL Injection Defense**: Strict parameterized queries across SQLAlchemy and asyncpg prevent SQL injection vulnerabilities.
- **Rate Limit Defense**: Rapid bursts exceeding 120 req/minute return HTTP 429 (`Too Many Requests`) with a standard `Retry-After` header.
