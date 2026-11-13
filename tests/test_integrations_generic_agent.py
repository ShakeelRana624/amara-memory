"""Tests for AMARA Generic Python Agent memory wrapper."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from amara.integrations.generic_agent import AmaraAgentMemory
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
async def test_agent_memory_async_lifecycle(async_engine: MemoryEngine) -> None:
    agent = AmaraAgentMemory(
        engine=async_engine,
        agent_id="test_agent",
        namespace="generic_test_ws",
    )

    # 1. Learn fact
    fact_item = await agent.alearn_fact(
        "User prefers dark theme and terminal outputs.",
        importance=0.9,
    )
    assert fact_item.id is not None

    # 2. Learn procedure
    proc_item = await agent.alearn_procedure(
        "To restart dev server, press Ctrl+C and run npm run dev.",
        importance=0.85,
    )
    assert proc_item.id is not None

    # 3. Before step retrieval
    ctx = await agent.abefore_step(query="What theme does the user like?")
    assert "dark theme" in ctx.formatted_context
    assert len(ctx.citations) >= 1

    # Augment prompt test
    augmented = ctx.augment_prompt("Generate CSS settings")
    assert "VERIFIED COGNITIVE MEMORY" in augmented
    assert "Generate CSS settings" in augmented

    # 4. After step persistence
    turn = await agent.aafter_step(
        user_message="Generate CSS settings",
        agent_response="Applied theme: dark.",
        session_id="sess_01",
    )
    assert turn.id is not None

    # 5. Forget memory
    success = await agent.aforget(fact_item.id)
    assert success is True


def test_agent_memory_sync_lifecycle(sync_engine: SyncMemoryEngine) -> None:
    agent = AmaraAgentMemory(
        engine=sync_engine,
        agent_id="sync_agent",
        namespace="sync_agent_ws",
    )

    # Learn fact
    item = agent.learn_fact("Sync fact: memory persistence is active.")
    assert item.id is not None

    # Learn procedure
    proc = agent.learn_procedure("Sync procedure: follow step 1 then step 2.")
    assert proc.id is not None

    # Before step
    ctx = agent.before_step(query="memory persistence")
    assert "persistence is active" in ctx.formatted_context

    # After step
    turn = agent.after_step(
        user_message="Is memory working?",
        agent_response="Yes, sync memory is operational.",
    )
    assert turn.id is not None
