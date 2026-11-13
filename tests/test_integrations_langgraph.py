"""Tests for AMARA LangGraph cognitive memory adapter."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from amara.enums import MemoryCategory
from amara.integrations.langgraph import AmaraLangGraphAdapter
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine


@pytest.fixture
async def async_engine() -> MemoryEngine:
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()
    return engine


@pytest.fixture
def sync_engine() -> Generator[SyncMemoryEngine, None, None]:
    config = MemoryConfig(storage_backend="memory")
    engine = SyncMemoryEngine(config=config)
    yield engine
    engine.close()


@pytest.mark.asyncio
async def test_langgraph_pre_retrieval_and_post_extraction(async_engine: MemoryEngine) -> None:
    # 1. Setup adapter
    adapter = AmaraLangGraphAdapter(engine=async_engine, default_namespace="test_ws")

    # Ingest baseline rule
    await async_engine.remember(
        content="PostgreSQL 16 connection pooling requires PgBouncer.",
        memory_type=MemoryCategory.SEMANTIC,
        namespace="test_ws",
    )

    # 2. Test pre-retrieval node
    pre_node = adapter.create_pre_retrieval_node(
        query_key="query",
        context_key="context",
        budget_tokens=512,
    )

    state: dict[str, str] = {"query": "What pooling proxy should we use for PostgreSQL?"}
    out_1 = await pre_node(state)
    assert "context" in out_1
    assert "PgBouncer" in out_1["context"]
    assert len(out_1["citations"]) >= 1

    # 3. Test post-extraction node
    post_node = adapter.create_post_extraction_node(
        user_input_key="query",
        agent_output_key="response",
        extracted_memory_id_key="saved_id",
    )
    state_turn = {
        "query": "How many connections?",
        "response": "Configure 50 max client connections in PgBouncer.",
    }
    out_2 = await post_node(state_turn)
    assert out_2["saved_id"] is not None

    # Verify turn is now searchable
    recall_res = await async_engine.recall("max client connections", namespace="test_ws")
    assert len(recall_res.results) >= 1


@pytest.mark.asyncio
async def test_langgraph_memory_actions(async_engine: MemoryEngine) -> None:
    adapter = AmaraLangGraphAdapter(engine=async_engine, default_namespace="action_ws")
    action_node = adapter.create_memory_action_node()

    # Remember action
    state_rem = {
        "memory_action": {
            "action": "remember",
            "content": "Secret API token key rotation period is 30 days.",
            "memory_type": "semantic",
        }
    }
    res_rem = await action_node(state_rem)
    assert res_rem["memory_action_result"]["status"] == "remembered"
    mem_id = res_rem["memory_action_result"]["memory_id"]

    # Update action
    state_upd = {
        "memory_action": {
            "action": "update",
            "memory_id": mem_id,
            "content": "Secret API token key rotation period is 60 days.",
        }
    }
    res_upd = await action_node(state_upd)
    assert res_upd["memory_action_result"]["status"] == "updated"

    # Forget action
    state_del = {
        "memory_action": {
            "action": "forget",
            "memory_id": mem_id,
            "hard": False,
        }
    }
    res_del = await action_node(state_del)
    assert res_del["memory_action_result"]["status"] == "tombstoned"


@pytest.mark.asyncio
async def test_langgraph_shared_project_node(async_engine: MemoryEngine) -> None:
    adapter = AmaraLangGraphAdapter(engine=async_engine)
    project_node = adapter.create_shared_project_node(
        project_id_key="proj_id",
        query_key="query",
        project_context_key="shared_knowledge",
    )

    # Preload knowledge in project namespace
    await async_engine.remember(
        content="Project AMARA uses Ruff for linting and formatting.",
        memory_type=MemoryCategory.SEMANTIC,
        namespace="project_amara_core",
    )

    state = {
        "proj_id": "amara_core",
        "query": "What tool do we use for code formatting?",
    }
    res = await project_node(state)
    assert "shared_knowledge" in res
    assert "Ruff" in res["shared_knowledge"]


def test_langgraph_sync_adapter(sync_engine: SyncMemoryEngine) -> None:
    adapter = AmaraLangGraphAdapter(engine=sync_engine, default_namespace="sync_ws")

    sync_engine.remember(
        content="Sync LangGraph node test item.",
        memory_type=MemoryCategory.SEMANTIC,
        namespace="sync_ws",
    )

    pre_node = adapter.create_pre_retrieval_node(query_key="query", context_key="ctx")
    out = pre_node({"query": "node test item"})
    assert "ctx" in out
    assert "Sync LangGraph" in out["ctx"]
