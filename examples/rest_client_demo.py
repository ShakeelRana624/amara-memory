"""AMARA REST API Client Demonstration.

Demonstrates calling AMARA REST endpoints using an HTTP client:
1. Health check and diagnostics (GET /api/v1/health).
2. Provisioning scoped API keys (POST /api/v1/auth/keys).
3. Ingesting memory propositions (POST /api/v1/memories).
4. Retrieving and inspecting memories (GET /api/v1/memories/{id}).
5. Multi-channel hybrid search (POST /api/v1/memories/search).
6. Grounded context reconstruction (POST /api/v1/context/reconstruct).
7. Tenant usage distribution (GET /api/v1/usage).
8. Controlled deletion (DELETE /api/v1/memories/{id}).
"""

from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore


async def main() -> None:
    # 1. Initialize engine and authentication key store
    print("--- 1. Setting Up Server Engine & API Key Store ---")
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    # Provision master admin key for tenant 'tenant_acme'
    _, admin_raw_key = key_store.create_key(
        tenant_id="tenant_acme",
        name="Admin Key",
        scopes={"read", "write", "admin"},
    )
    print(f"Master Admin Key: {admin_raw_key[:18]}... (secret hashed)")

    # Build FastAPI application
    app = create_app(engine=engine, key_store=key_store)

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Check Service Health
        print("\n--- 2. Health Check (GET /api/v1/health) ---")
        res = await client.get("/api/v1/health")
        print(f"Status {res.status_code}: {res.json()}")

        # 3. Issue a Scoped Read/Write Key for standard Agent usage
        print("\n--- 3. Provision Agent API Key (POST /api/v1/auth/keys) ---")
        headers_admin = {"Authorization": f"Bearer {admin_raw_key}"}
        key_res = await client.post(
            "/api/v1/auth/keys",
            headers=headers_admin,
            json={
                "name": "Customer Support Agent Key",
                "scopes": ["read", "write"],
                "expires_in_days": 30,
            },
        )
        agent_key_data = key_res.json()
        if key_res.status_code != 201:
            print(f"Error provisioning key ({key_res.status_code}): {agent_key_data}")
            return
        agent_raw_key = agent_key_data["raw_key"]
        print(f"Agent Key ID: {agent_key_data['key_id']}")
        print(f"Scopes: {agent_key_data['scopes']}")

        headers_agent = {"Authorization": f"Bearer {agent_raw_key}"}

        # 4. Ingest Observations
        print("\n--- 4. Ingest Memories (POST /api/v1/memories) ---")
        observations = [
            {
                "content": "User prefer dark theme with high contrast enabled in settings.",
                "author_id": "settings_agent",
                "memory_type": "semantic",
                "importance": 0.8,
            },
            {
                "content": "Database migration v3.4 failed at 03:00 UTC due to locked table.",
                "author_id": "devops_monitor",
                "memory_type": "episodic",
                "importance": 0.9,
            },
            {
                "content": "Customer account Tier is Enterprise with 99.99% SLA commitment.",
                "author_id": "crm_sync",
                "memory_type": "semantic",
                "importance": 0.95,
            },
        ]

        stored_ids: list[str] = []
        for obs in observations:
            m_res = await client.post("/api/v1/memories", headers=headers_agent, json=obs)
            if m_res.status_code != 201:
                print(f"Error creating memory ({m_res.status_code}): {m_res.json()}")
                return
            data = m_res.json()["data"]
            stored_ids.append(data["id"])
            print(f"Stored: {data['id']} [{data['memory_type']}] -> {data['content']}")

        # 5. Hybrid Search
        print("\n--- 5. Hybrid Search (POST /api/v1/memories/search) ---")
        search_res = await client.post(
            "/api/v1/memories/search",
            headers=headers_agent,
            json={"query": "database failure incident", "top_k": 5},
        )
        search_data = search_res.json()
        print(
            f"Latency: {search_data['latency_ms']:.2f}ms | Matches: {len(search_data['results'])}"
        )
        for match in search_data["results"]:
            print(f"  Score: {match['relevance_score']:.2f} | {match['item']['content']}")

        # 6. Reconstruct Grounded Context Prompt
        print("\n--- 6. Context Reconstruction (POST /api/v1/context/reconstruct) ---")
        ctx_res = await client.post(
            "/api/v1/context/reconstruct",
            headers=headers_agent,
            json={"query": "What is the customer SLA and database status?", "budget_tokens": 500},
        )
        ctx_data = ctx_res.json()
        print(
            f"Tokens Used: {ctx_data['total_tokens_used']} | Remaining: {ctx_data['remaining_token_budget']}"
        )
        print(f"Abstention Recommended: {ctx_data['abstention_recommended']}")
        print("\nFormatted Prompt Block:")
        print(ctx_data["formatted_context"])

        # 7. Tenant Usage Distribution
        print("\n--- 7. Tenant Usage (GET /api/v1/usage) ---")
        usage_res = await client.get("/api/v1/usage", headers=headers_agent)
        usage_data = usage_res.json()
        print(f"Total Memories: {usage_data['total_memories']}")
        print(f"By Category: {usage_data['by_category']}")
        print(f"Average Confidence: {usage_data['average_confidence']}")

        # 8. Soft Delete Memory
        print("\n--- 8. Controlled Deletion (DELETE /api/v1/memories/{id}) ---")
        target_id = stored_ids[0]
        del_res = await client.delete(f"/api/v1/memories/{target_id}", headers=headers_agent)
        print(f"Delete response: {del_res.json()}")

    await engine.close()
    print("\n--- Demo Completed Successfully ---")


if __name__ == "__main__":
    asyncio.run(main())
