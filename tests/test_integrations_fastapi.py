"""Tests for AMARA FastAPI integration client, dependencies, and middleware."""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from amara.integrations.fastapi import (
    AmaraClient,
    AmaraMemoryDependency,
)
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore


@pytest.fixture
async def amara_backend() -> tuple[FastAPI, str]:
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    key_store = APIKeyStore()
    _, raw_key = key_store.create_key(
        tenant_id="tenant_ext_app",
        name="Ext App Key",
        scopes={"read", "write", "admin"},
    )

    app = create_app(engine=engine, key_store=key_store)
    return app, raw_key


@pytest.mark.asyncio
async def test_amara_client_and_dependency(amara_backend: tuple[FastAPI, str]) -> None:
    backend_app, api_key = amara_backend
    transport = ASGITransport(app=backend_app)

    # 1. Instantiate AmaraClient with test transport
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        amara_client = AmaraClient(
            base_url="http://testserver",
            api_key=api_key,
            client=http_client,
        )

        # Check health
        health = await amara_client.check_health()
        assert health["status"] == "healthy"

        # Remember
        mem_res = await amara_client.remember(
            content="FastAPI service connected to AMARA cognitive cloud.",
            author_id="fastapi_worker",
            namespace="service_mesh",
        )
        assert mem_res["data"]["id"] is not None

        # Reconstruct context
        recon_res = await amara_client.reconstruct_context(
            query="FastAPI connection status",
            namespace="service_mesh",
            budget_tokens=512,
        )
        assert "cognitive cloud" in recon_res["formatted_context"]

        # Usage
        usage = await amara_client.get_usage(namespace="service_mesh")
        assert usage["total_memories"] >= 1


@pytest.mark.asyncio
async def test_third_party_fastapi_app_integration(amara_backend: tuple[FastAPI, str]) -> None:
    backend_app, api_key = amara_backend
    backend_transport = ASGITransport(app=backend_app)

    # Create a 3rd-party user application
    third_party_app = FastAPI(title="Customer Chatbot API")

    async with AsyncClient(
        transport=backend_transport, base_url="http://amara-backend"
    ) as http_client:
        memory_dep = AmaraMemoryDependency(
            base_url="http://amara-backend",
            api_key=api_key,
            client=http_client,
        )

        @third_party_app.post("/agent/chat")
        async def agent_chat(
            query: str,
            memory: AmaraClient = Depends(memory_dep),
        ) -> dict[str, str]:
            # Step A: Reconstruct context
            recon = await memory.reconstruct_context(query=query, namespace="cust_001")
            # Step B: Record turn
            await memory.remember(
                content=f"User asked: {query}",
                author_id="chat_user",
                namespace="cust_001",
            )
            return {"context": recon["formatted_context"], "reply": "Response generated"}

        # Test the 3rd-party app
        app_transport = ASGITransport(app=third_party_app)
        async with AsyncClient(transport=app_transport, base_url="http://user-app") as user_client:
            resp = await user_client.post("/agent/chat?query=hello%20world")
            assert resp.status_code == 200
            assert resp.json()["reply"] == "Response generated"
