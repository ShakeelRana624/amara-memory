# AMARA Developer Dashboard

A professional, minimal, modern developer console and analytics dashboard for the **AMARA (Adaptive Memory Architecture for Reasoning & AI)** cognitive memory platform.

Built with **Next.js 14 (App Router)**, **TypeScript**, **Tailwind CSS**, and dark/light technical themes.

---

## Features

- **Live Backend & Offline Sandbox**:
  - Automatically probes `GET /api/v1/health` on `http://localhost:8000`.
  - Seamless toggle for **Sample Sandbox Mode** with preloaded cognitive data for offline exploration without requiring a running PostgreSQL instance.
- **12 Interactive Developer Views**:
  1. **Landing & Product Overview (`/`)**: Technical architecture showcase, comparisons vs naive vector RAG, and copyable Python SDK snippets.
  2. **Sign In (`/login`)**: API Key authentication with advanced endpoint configuration and one-click Sandbox launch.
  3. **Workspace Provisioning (`/register`)**: Tenant onboarding with single-exposure Master API key generation.
  4. **Workspace Overview (`/dashboard`)**: KPI metric cards, cognitive category distribution, epistemic lifecycle state machine, recent memory propositions stream, and quick ingestion modal.
  5. **Projects & Workspaces (`/dashboard/workspaces`)**: Namespace partitioning for isolating multi-agent memory pools under the same tenant.
  6. **Memory Explorer (`/dashboard/memories`)**: Data table with live search, category/status filters, pagination, inline editing, and soft tombstone / hard purge actions.
  7. **Memory Detail & Provenance (`/dashboard/memories/[id]`)**: Full structural inspection of normalized propositions, source attribution, temporal interval validity, corroborating evidence items, and structured metadata.
  8. **Relationship Explorer (`/dashboard/relationships`)**: Associative graph edge viewer (`CONTRADICTS`, `DERIVED_FROM`, `DEPENDS_ON`, `CAUSAL`, `ASSOCIATED_WITH`).
  9. **Retrieval Playground (`/dashboard/retrieval`)**: Interactive testing console for hybrid, dense vector, lexical BM25, temporal recency, and relational graph search, plus token-bounded context prompt reconstruction with citations (`[REF-1]`, `[REF-2]`).
  10. **API Key Management (`/dashboard/keys`)**: Scoped credential issuance (`read`, `write`, `admin`), key rotation, revocation, and single-exposure secret reveal modals.
  11. **Usage & Analytics (`/dashboard/usage`)**: Category distribution bars, state machine status counts, and epistemic certainty vs cognitive importance metrics.
  12. **Settings (`/dashboard/settings`)**: API Base URL probe test, tenant ID scope, decay half-life, default token budget, and hard purge safeguards.
  13. **Documentation (`/dashboard/docs`)**: Interactive API reference with copyable `curl` commands and Python SDK guide.

---

## Getting Started

### 1. Start AMARA Backend Server
In the repository root:
```bash
# Start PostgreSQL (or run with in-memory storage backend)
uv run uvicorn amara.server.app:create_app --factory --port 8000 --reload
```

### 2. Run Dashboard Development Server
In `dashboard/`:
```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Build Production Bundle
```bash
npm run build
npm start
```
