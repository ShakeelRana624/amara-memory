"""Integration test suite for AMARA FastAPI REST API endpoints and middlewares."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore


@pytest.fixture
async def app_and_keys() -> AsyncGenerator[dict[str, Any], None]:
    """Create test application, in-memory engine, and tenant API keys."""
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, admin_key = key_store.create_key(
        tenant_id="tenant_main",
        name="Admin Key",
        scopes={"read", "write", "admin"},
    )
    _, agent_key = key_store.create_key(
        tenant_id="tenant_main",
        name="Agent Key",
        scopes={"read", "write"},
    )
    _, other_tenant_key = key_store.create_key(
        tenant_id="tenant_stranger",
        name="Stranger Key",
        scopes={"read", "write"},
    )

    app = create_app(engine=engine, key_store=key_store)

    yield {
        "app": app,
        "engine": engine,
        "admin_key": admin_key,
        "agent_key": agent_key,
        "other_tenant_key": other_tenant_key,
    }

    await engine.close()


@pytest.mark.asyncio
async def test_health_endpoint(app_and_keys: dict[str, Any]) -> None:
    """Verify health endpoint is publicly accessible and reports system status."""
    app = app_and_keys["app"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["storage_backend"] == "memory"
        assert "timestamp" in data
        assert "X-Request-ID" in res.headers


@pytest.mark.asyncio
async def test_memories_crud_and_search_endpoints(app_and_keys: dict[str, Any]) -> None:
    """Verify memory creation, retrieval, patching, search, and deletion via REST API."""
    app = app_and_keys["app"]
    headers = {"Authorization": f"Bearer {app_and_keys['agent_key']}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Memory
        create_res = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "User prefers asynchronous Python programming with FastAPI.",
                "author_id": "ide_extension",
                "memory_type": "semantic",
                "importance": 0.85,
            },
        )
        assert create_res.status_code == 201
        mem = create_res.json()["data"]
        memory_id = mem["id"]
        assert mem["tenant_id"] == "tenant_main"
        assert mem["status"] == "active"
        assert "asynchronous Python" in mem["content"]

        # 2. Get Memory by ID
        get_res = await client.get(f"/api/v1/memories/{memory_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["data"]["id"] == memory_id

        # 3. Patch Memory
        patch_res = await client.patch(
            f"/api/v1/memories/{memory_id}",
            headers=headers,
            json={
                "content": "User prefers async Python with FastAPI and uv package manager.",
                "metadata": {"preferred_tool": "uv"},
            },
        )
        assert patch_res.status_code == 200
        patched = patch_res.json()["data"]
        assert "uv package manager" in patched["content"]
        assert patched["version"] == 2
        assert patched["metadata"]["preferred_tool"] == "uv"

        # 4. Search Memories
        search_res = await client.post(
            "/api/v1/memories/search",
            headers=headers,
            json={"query": "FastAPI async", "top_k": 5},
        )
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["results"]) >= 1
        assert search_data["results"][0]["item"]["id"] == memory_id

        # 5. Delete Memory (Soft Tombstone)
        del_res = await client.delete(f"/api/v1/memories/{memory_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "tombstoned"

        # 6. Get Non-existent Memory -> 404
        bad_res = await client.get(f"/api/v1/memories/{uuid4()}", headers=headers)
        assert bad_res.status_code == 404


@pytest.mark.asyncio
async def test_context_reconstruction_endpoint(app_and_keys: dict[str, Any]) -> None:
    """Verify prompt context assembly endpoint via REST API."""
    app = app_and_keys["app"]
    headers = {"Authorization": f"Bearer {app_and_keys['agent_key']}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed memories
        await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "PostgreSQL pgvector extension enables semantic search.",
                "author_id": "architect",
                "memory_type": "semantic",
            },
        )

        res = await client.post(
            "/api/v1/context/reconstruct",
            headers=headers,
            json={"query": "pgvector semantic search", "budget_tokens": 400},
        )
        assert res.status_code == 200
        ctx = res.json()
        assert ctx["abstention_recommended"] is False
        assert len(ctx["citations"]) >= 1
        assert "PostgreSQL" in ctx["formatted_context"]
        assert ctx["total_tokens_used"] > 0


@pytest.mark.asyncio
async def test_consolidation_and_usage_endpoints(app_and_keys: dict[str, Any]) -> None:
    """Verify consolidation and usage telemetry endpoints."""
    app = app_and_keys["app"]
    headers = {"Authorization": f"Bearer {app_and_keys['agent_key']}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ingest episodic memory
        await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "Worker process completed ETL job #402 in 42 seconds.",
                "author_id": "etl_job",
                "memory_type": "episodic",
            },
        )

        # Trigger Consolidation
        cons_res = await client.post(
            "/api/v1/memories/consolidate",
            headers=headers,
            json={"namespace": "default"},
        )
        assert cons_res.status_code == 200
        assert cons_res.json()["tenant_id"] == "tenant_main"

        # Check Usage
        usage_res = await client.get("/api/v1/usage", headers=headers)
        assert usage_res.status_code == 200
        usage = usage_res.json()
        assert usage["total_memories"] >= 1
        assert usage["tenant_id"] == "tenant_main"


@pytest.mark.asyncio
async def test_cross_tenant_isolation_prevention(app_and_keys: dict[str, Any]) -> None:
    """Verify that Tenant B cannot access or delete Tenant A's memories."""
    app = app_and_keys["app"]
    headers_a = {"Authorization": f"Bearer {app_and_keys['agent_key']}"}
    headers_b = {"Authorization": f"Bearer {app_and_keys['other_tenant_key']}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tenant A creates private memory
        res_a = await client.post(
            "/api/v1/memories",
            headers=headers_a,
            json={
                "content": "Secret credentials for internal database cluster.",
                "author_id": "sec_agent",
                "memory_type": "semantic",
            },
        )
        mem_id = res_a.json()["data"]["id"]

        # Tenant B attempts to read Tenant A's memory -> 404 Not Found (isolated)
        get_res = await client.get(f"/api/v1/memories/{mem_id}", headers=headers_b)
        assert get_res.status_code == 404

        # Tenant B attempts to delete Tenant A's memory -> 404 Not Found
        del_res = await client.delete(f"/api/v1/memories/{mem_id}", headers=headers_b)
        assert del_res.status_code == 404


@pytest.mark.asyncio
async def test_rate_limiting_middleware() -> None:
    """Verify rate limiter blocks requests exceeding configured quota with 429."""
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, test_key = key_store.create_key(tenant_id="tenant_rl", scopes={"read", "write"})

    # App with tight rate limit: 2 requests per minute
    app = create_app(engine=engine, key_store=key_store, rate_limit_per_minute=2)
    headers = {"Authorization": f"Bearer {test_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1st request -> 200
        r1 = await client.get("/api/v1/usage", headers=headers)
        assert r1.status_code == 200

        # 2nd request -> 200
        r2 = await client.get("/api/v1/usage", headers=headers)
        assert r2.status_code == 200

        # 3rd request -> 429 Too Many Requests
        r3 = await client.get("/api/v1/usage", headers=headers)
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers

    await engine.close()


@pytest.mark.asyncio
async def test_payload_size_limit_middleware() -> None:
    """Verify payload size limit rejects oversized bodies with 413."""
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, test_key = key_store.create_key(tenant_id="tenant_size", scopes={"read", "write"})

    # Max 100 bytes allowed
    app = create_app(engine=engine, key_store=key_store, max_request_bytes=100)
    headers = {"Authorization": f"Bearer {test_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Oversized body (> 100 bytes)
        big_content = "X" * 300
        res = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={"content": big_content, "author_id": "test"},
        )
        assert res.status_code == 413

    await engine.close()


@pytest.mark.asyncio
async def test_request_validation_errors() -> None:
    """Verify malformed JSON requests return 422 with structured error envelope."""
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, test_key = key_store.create_key(tenant_id="tenant_val", scopes={"read", "write"})

    app = create_app(engine=engine, key_store=key_store)
    headers = {"Authorization": f"Bearer {test_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing required 'content' field
        res = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={"author_id": "test"},
        )
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "X-Request-ID" in res.headers

    await engine.close()
