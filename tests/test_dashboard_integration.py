"""End-to-end API integration tests verifying developer dashboard contracts."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore


@pytest.fixture
def key_store() -> APIKeyStore:
    return APIKeyStore()


@pytest.fixture
def master_key(key_store: APIKeyStore) -> str:
    _, raw_key = key_store.create_key(
        tenant_id="tenant-dashboard-test",
        name="Dashboard Master Admin Key",
        scopes=["read", "write", "admin"],
    )
    return raw_key


@pytest.mark.asyncio
async def test_dashboard_full_user_journey(key_store: APIKeyStore, master_key: str) -> None:
    """Test full developer journey matching the developer dashboard flows."""
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    app = create_app(engine=engine, key_store=key_store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health Probe Check (Public, no auth)
        health_res = await client.get("/api/v1/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "healthy"
        assert "version" in health_data

        headers = {"Authorization": f"Bearer {master_key}"}

        # 2. Key Management: List keys
        keys_res = await client.get("/api/v1/auth/keys", headers=headers)
        assert keys_res.status_code == 200
        keys_list = keys_res.json()
        assert len(keys_list) >= 1

        # 3. Key Management: Issue a secondary scoped key
        create_key_res = await client.post(
            "/api/v1/auth/keys",
            headers=headers,
            json={
                "name": "Dashboard Secondary Key",
                "scopes": ["read", "write"],
                "expires_in_days": 30,
            },
        )
        assert create_key_res.status_code == 201
        new_key_data = create_key_res.json()
        assert "raw_key" in new_key_data
        sec_key_id = new_key_data["key_id"]

        # 4. Key Management: Rotate secondary key
        rotate_res = await client.post(
            f"/api/v1/auth/keys/{sec_key_id}/rotate",
            headers=headers,
        )
        assert rotate_res.status_code == 200
        rotated_data = rotate_res.json()
        assert rotated_data["key_id"] == sec_key_id
        assert rotated_data["raw_key"] != new_key_data["raw_key"]

        # 5. Key Management: Revoke secondary key
        revoke_res = await client.delete(
            f"/api/v1/auth/keys/{sec_key_id}",
            headers=headers,
        )
        assert revoke_res.status_code == 200
        assert revoke_res.json()["status"] == "revoked"

        # 6. Memory Ingestion: Remember 3 propositions in a namespace
        ns = "dashboard-e2e-ws"
        p1 = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "User selected PostgreSQL 16 with pgvector extension.",
                "author_id": "test_engineer",
                "memory_type": "semantic",
                "confidence": 0.99,
                "importance": 0.90,
                "namespace": ns,
            },
        )
        assert p1.status_code == 201
        m1_id = p1.json()["data"]["id"]

        p2 = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "Connection pool uses PgBouncer in transaction pooling mode on port 6432.",
                "author_id": "test_engineer",
                "memory_type": "episodic",
                "confidence": 0.95,
                "importance": 0.85,
                "namespace": ns,
            },
        )
        assert p2.status_code == 201

        p3 = await client.post(
            "/api/v1/memories",
            headers=headers,
            json={
                "content": "Staging server is staging-db.internal.amara.net.",
                "author_id": "test_engineer",
                "memory_type": "working",
                "confidence": 0.80,
                "importance": 0.40,
                "namespace": ns,
            },
        )
        assert p3.status_code == 201

        # 7. Memory Inspection: Retrieve single memory by ID
        get_res = await client.get(f"/api/v1/memories/{m1_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["data"]["id"] == m1_id

        # 8. Memory Update: Controlled update of proposition
        patch_res = await client.patch(
            f"/api/v1/memories/{m1_id}",
            headers=headers,
            json={"content": "User confirmed PostgreSQL 16 with pgvector 0.7.0."},
        )
        assert patch_res.status_code == 200
        assert (
            patch_res.json()["data"]["content"]
            == "User confirmed PostgreSQL 16 with pgvector 0.7.0."
        )
        assert patch_res.json()["data"]["version"] == 2

        # 9. Multi-Channel Hybrid Search: Query memories
        search_res = await client.post(
            "/api/v1/memories/search",
            headers=headers,
            json={
                "query": "PostgreSQL PgBouncer connection",
                "namespace": ns,
                "strategy": "hybrid",
                "top_k": 5,
            },
        )
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["results"]) >= 1

        # 10. Context Prompt Reconstruction: Knapsack packing with citations
        recon_res = await client.post(
            "/api/v1/context/reconstruct",
            headers=headers,
            json={
                "query": "What is the database connection architecture?",
                "namespace": ns,
                "budget_tokens": 1024,
                "strategy": "hybrid",
            },
        )
        assert recon_res.status_code == 200
        recon_data = recon_res.json()
        assert "formatted_context" in recon_data
        assert recon_data["total_tokens_used"] > 0
        assert len(recon_data["citations"]) >= 1

        # 11. Consolidation Trigger: Trigger episodic consolidation
        consol_res = await client.post(
            "/api/v1/memories/consolidate",
            headers=headers,
            json={"namespace": ns},
        )
        assert consol_res.status_code == 200
        assert "consolidated_count" in consol_res.json()

        # 12. Usage Metrics Telemetry: Check stats for tenant & namespace
        usage_res = await client.get(f"/api/v1/usage?namespace={ns}", headers=headers)
        assert usage_res.status_code == 200
        usage_data = usage_res.json()
        assert usage_data["total_memories"] >= 2
        assert "by_category" in usage_data
        assert "by_status" in usage_data

        # 13. Memory Deletion: Soft tombstone
        del_res = await client.delete(f"/api/v1/memories/{m1_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "tombstoned"
