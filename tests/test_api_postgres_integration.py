"""PostgreSQL integration tests for AMARA Public SDK and FastAPI REST Engine."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from amara.enums import MemoryCategory
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore
from amara.storage.database import DatabaseManager

TEST_DB_URL = "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"


async def _is_postgres_available() -> bool:
    try:
        mgr = DatabaseManager(TEST_DB_URL, pool_size=1, max_overflow=0)
        await mgr.initialize()
        async with mgr.session() as s:
            await s.execute(text("SELECT 1;"))
        await mgr.close()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
async def check_postgres() -> None:
    if not await _is_postgres_available():
        pytest.skip("PostgreSQL test database is unavailable at 127.0.0.1:5432.")


@pytest.fixture
async def clean_database() -> AsyncGenerator[None, None]:
    """Clean test tables before and after test execution."""
    mgr = DatabaseManager(TEST_DB_URL, pool_size=2, max_overflow=2)
    await mgr.initialize()
    async with mgr.session() as session:
        await session.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        await session.execute(
            text(
                "TRUNCATE TABLE memory_events, memory_version_history, "
                "memory_relationships, memory_records CASCADE;"
            )
        )
    yield
    async with mgr.session() as session:
        await session.execute(text("SET LOCAL app.bypass_rls = 'on';"))
        await session.execute(
            text(
                "TRUNCATE TABLE memory_events, memory_version_history, "
                "memory_relationships, memory_records CASCADE;"
            )
        )
    await mgr.close()


@pytest.mark.asyncio
async def test_sdk_postgres_engine(clean_database: None) -> None:
    """Verify asynchronous MemoryEngine backed by real PostgreSQL 16 + pgvector."""
    config = MemoryConfig(
        storage_backend="postgres",
        database_url=TEST_DB_URL,
        db_pool_size=5,
        db_max_overflow=5,
        default_tenant_id="tenant_pg_sdk",
    )

    async with MemoryEngine(config=config) as engine:
        # Ingest
        mem = await engine.remember(
            content="PostgreSQL 16 partitioned tables with pgvector index.",
            author_id="db_architect",
            memory_type=MemoryCategory.SEMANTIC,
            importance=0.9,
        )
        assert mem.id is not None
        assert mem.tenant_id == "tenant_pg_sdk"

        # Inspect
        inspection = await engine.inspect(mem.id)
        assert inspection.record.id == mem.id
        assert "partitioned tables" in inspection.record.content

        # Update
        updated = await engine.update(
            memory_id=mem.id,
            new_content="PostgreSQL 16 partitioned tables with HNSW vector index.",
        )
        assert updated.version == 2
        assert "HNSW" in updated.content

        # Recall
        recall_res = await engine.recall(query="pgvector HNSW index")
        assert len(recall_res.results) >= 1
        assert recall_res.results[0].item.id == mem.id

        # Stats
        stats = await engine.stats()
        assert stats.total_memories == 1

        # Delete
        success = await engine.forget(mem.id, hard=False)
        assert success is True


@pytest.mark.asyncio
async def test_rest_api_postgres_backend(clean_database: None) -> None:
    """Verify full FastAPI REST API running against PostgreSQL with concurrent load."""
    config = MemoryConfig(
        storage_backend="postgres",
        database_url=TEST_DB_URL,
        db_pool_size=10,
        db_max_overflow=10,
        default_tenant_id="tenant_pg_api",
    )

    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, api_key = key_store.create_key(
        tenant_id="tenant_pg_api",
        name="Postgres API Key",
        scopes={"read", "write"},
    )

    app = create_app(engine=engine, key_store=key_store, rate_limit_per_minute=200)
    headers = {"Authorization": f"Bearer {api_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check with real DB connection status
        h_res = await client.get("/api/v1/health")
        assert h_res.status_code == 200
        assert h_res.json()["database_connected"] is True
        assert h_res.json()["storage_backend"] == "postgres"

        # 2. Ingest 10 memories concurrently
        async def _ingest_item(idx: int) -> str:
            res = await client.post(
                "/api/v1/memories",
                headers=headers,
                json={
                    "content": f"System event #{idx}: Redis cluster failover completed successfully.",
                    "author_id": f"worker_{idx}",
                    "memory_type": "episodic",
                    "importance": 0.75,
                },
            )
            assert res.status_code == 201
            return str(res.json()["data"]["id"])

        created_ids = await asyncio.gather(*[_ingest_item(i) for i in range(10)])
        assert len(created_ids) == 10
        assert len(set(created_ids)) == 10

        # 3. Hybrid Search against PostgreSQL
        search_res = await client.post(
            "/api/v1/memories/search",
            headers=headers,
            json={"query": "Redis cluster failover", "top_k": 5},
        )
        assert search_res.status_code == 200
        matches = search_res.json()["results"]
        assert len(matches) >= 1
        assert "Redis cluster" in matches[0]["item"]["content"]

        # 4. Context Reconstruction against PostgreSQL
        ctx_res = await client.post(
            "/api/v1/context/reconstruct",
            headers=headers,
            json={"query": "Redis failover status", "budget_tokens": 500},
        )
        assert ctx_res.status_code == 200
        ctx_data = ctx_res.json()
        assert not ctx_data["abstention_recommended"]
        assert len(ctx_data["citations"]) >= 1

        # 5. Usage telemetry against PostgreSQL
        usage_res = await client.get("/api/v1/usage", headers=headers)
        assert usage_res.status_code == 200
        assert usage_res.json()["total_memories"] == 10

    await engine.close()
