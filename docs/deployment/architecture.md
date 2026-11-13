# AMARA Production Architecture & Deployment Topology

This document describes the enterprise production deployment topology, network boundaries, and service architecture for the AMARA cognitive memory platform.

---

## Architecture Overview

```
                                [ Public Internet / Clients ]
                                              │
                                              │ HTTPS (Port 443 / TLS 1.3)
                                              ▼
                    ┌──────────────────────────────────────────────────┐
                    │          Caddy / Nginx Ingress Gateway           │
                    │   - Automatic TLS 1.3 / Certificate Rotation     │
                    │   - Security Headers (HSTS, CSP, X-Frame-Options)│
                    │   - Global Rate Limiting (100 req/s, burst 200)  │
                    │   - Gzip / Zstd Compression                      │
                    └────────────┬────────────────────────┬────────────┘
                                 │                        │
               /api/*, /docs     │                        │ /* (UI assets)
                                 ▼                        ▼
        ┌───────────────────────────────────┐   ┌───────────────────────────────┐
        │       FastAPI API Cluster         │   │   Next.js 14 Dashboard Cluster│
        │   - 4 Uvicorn Workers per node    │   │   - Standalone Node.js Runner │
        │   - Stateless REST Endpoints      │   │   - SSR & Client Hydration    │
        │   - HMAC-SHA256 Auth & Revocation │   │   - Tenant Sandboxing         │
        │   - Liveness / Readiness Probes   │   │   - Non-root user (nextjs)    │
        └─────────────────┬─────────────────┘   └───────────────────────────────┘
                          │
                          │ PostgreSQL Async Connection Pool (asyncpg)
                          ▼
        ┌───────────────────────────────────────────────────────────────┐
        │        Managed PostgreSQL 16+ with pgvector Extension         │
        │   - memory_records, memory_relationships, memory_events       │
        │   - Row-Level Security (RLS) with Tenant Isolation            │
        │   - HNSW / IVFFlat Cosine Similarity Indexes                  │
        │   - GIN / Trigram Lexical Search Indexes                      │
        │   - Continuous WAL Archiving & Daily Encrypted Snapshots      │
        └─────────────────▲─────────────────────────────────────────────┘
                          │
                          │ Periodic Maintenance Connection Pool
                          │
        ┌─────────────────┴─────────────────┐
        │    AMARA Background Worker        │
        │   - Salience Half-Life Decay      │
        │   - Memory Consolidation Loop     │
        │   - TTL Temporal Expiration Scan  │
        │   - Tombstone Retention Purge     │
        │   - Heartbeat Liveness Probe      │
        └───────────────────────────────────┘
```

---

## Service Specifications

### 1. Ingress Gateway (`gateway`)
- **Technology**: Caddy 2 or Nginx.
- **TLS**: Automated TLS 1.3 certificate provisioning via Let's Encrypt / ZeroSSL.
- **Security Headers**:
  - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **Rate Limiting**: 100 requests/sec per IP, burst up to 200.

### 2. FastAPI API Service (`api`)
- **Technology**: Python 3.12, FastAPI, Uvicorn (ASGI).
- **Process Model**: 4 Uvicorn workers per container instance.
- **Resource Limits**: 2.0 vCPU, 1.5 GB RAM.
- **Port**: 8000 (Internal cluster network).
- **Health Checks**:
  - Liveness: `GET /api/v1/health` (15s interval, 5s timeout).
  - Readiness: Database ping and schema migration check.

### 3. Developer Dashboard (`dashboard`)
- **Technology**: Next.js 14 (App Router), TypeScript, Tailwind CSS.
- **Port**: 3000 (Internal cluster network).
- **User**: Non-root `nextjs` (UID: 1001).
- **Resource Limits**: 1.0 vCPU, 1.0 GB RAM.

### 4. Background Lifecycle Worker (`worker`)
- **Technology**: Python 3.12 async maintenance loop.
- **Cadence**: Configurable 60-second cycle.
- **Tasks**:
  - Temporal TTL expiration scans.
  - Multi-attribute salience decay calculation.
  - Near-duplicate clustering and consolidation.
  - Tombstone cleanup for records outside legal hold retention locks.
- **Health Check**: Heartbeat timestamp inspection (`/tmp/amara/worker-heartbeat`).

### 5. PostgreSQL Storage Tier (`postgres`)
- **Engine**: PostgreSQL 16+ with `pgvector` extension.
- **Isolation**: Tenant separation via Row-Level Security (`app.current_tenant_id`).
- **Connection Pooling**: SQLAlchemy async engine with `asyncpg` (pool_size=30, max_overflow=20).

