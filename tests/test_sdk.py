"""Unit and functional test suite for AMARA Public Python SDK (async and sync)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from amara.enums import LifecycleStatus, MemoryCategory
from amara.exceptions import MemoryNotFoundError
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine


@pytest.mark.asyncio
async def test_memory_engine_lifecycle_and_crud() -> None:
    """Verify asynchronous MemoryEngine initialization, CRUD, and cleanup."""
    config = MemoryConfig(storage_backend="memory", default_tenant_id="tenant_sdk_test")

    async with MemoryEngine(config=config) as engine:
        # 1. Remember / Ingest
        mem1 = await engine.remember(
            content="Alex specializes in distributed systems and consensus protocols.",
            author_id="recruiter_agent",
            memory_type=MemoryCategory.SEMANTIC,
            confidence=0.95,
            importance=0.85,
            metadata={"skill": "distributed_systems"},
        )
        assert mem1.id is not None
        assert mem1.tenant_id == "tenant_sdk_test"
        assert mem1.memory_type == MemoryCategory.SEMANTIC
        assert mem1.status == LifecycleStatus.ACTIVE
        assert "distributed systems" in mem1.content

        # 2. Inspect
        inspection = await engine.inspect(mem1.id)
        assert inspection.record.id == mem1.id
        assert inspection.record.content == mem1.content
        assert isinstance(inspection.relationships, tuple)
        assert isinstance(inspection.evidence, tuple)

        # 3. Update
        updated = await engine.update(
            memory_id=mem1.id,
            new_content="Alex specializes in distributed systems, Raft, and Paxos consensus.",
            metadata_updates={"verified": True},
        )
        assert updated.id == mem1.id
        assert updated.version == 2
        assert "Raft" in updated.content
        assert updated.metadata.get("verified") is True

        # 4. Recall
        recall_res = await engine.recall(
            query="consensus protocols",
            strategy=RetrievalStrategy.HYBRID,
            top_k=5,
        )
        assert len(recall_res.results) >= 1
        assert any(r.item.id == mem1.id for r in recall_res.results)
        top_match = recall_res.results[0]
        assert top_match.relevance_score > 0
        assert top_match.match_explanation is not None

        # 5. Stats
        stats = await engine.stats()
        assert stats.tenant_id == "tenant_sdk_test"
        assert stats.total_memories == 1
        assert stats.by_category.get(MemoryCategory.SEMANTIC.value) == 1
        assert stats.by_status.get(LifecycleStatus.ACTIVE.value) == 1

        # 6. Archive and Restore
        archived = await engine.archive(mem1.id)
        assert archived.status == LifecycleStatus.ARCHIVED

        restored = await engine.restore(mem1.id)
        assert restored.status == LifecycleStatus.ACTIVE

        # 7. Forget (Soft tombstone)
        deleted = await engine.forget(mem1.id, hard=False)
        assert deleted is True

        # Verifying tombstoned record is excluded from active stats and recall
        stats_after = await engine.stats()
        assert stats_after.total_memories == 0


@pytest.mark.asyncio
async def test_memory_engine_context_reconstruction() -> None:
    """Verify context prompt reconstruction using the SDK facade."""
    config = MemoryConfig(storage_backend="memory", default_tenant_id="tenant_ctx")

    async with MemoryEngine(config=config) as engine:
        await engine.remember(
            content="PostgreSQL pgvector extension enables HNSW indexing.",
            author_id="db_admin",
            memory_type=MemoryCategory.SEMANTIC,
            importance=0.9,
        )
        await engine.remember(
            content="API rate limiting is configured at 120 requests per minute.",
            author_id="gateway_agent",
            memory_type=MemoryCategory.SEMANTIC,
            importance=0.7,
        )

        context = await engine.reconstruct(
            query="pgvector index and rate limit",
            budget=400,
        )
        assert not context.abstention_recommended
        assert len(context.citations) >= 1
        assert "PostgreSQL" in context.formatted_context
        assert context.total_tokens_used > 0
        assert context.remaining_token_budget <= 400


@pytest.mark.asyncio
async def test_memory_engine_consolidation() -> None:
    """Verify episodic memory consolidation via the SDK."""
    config = MemoryConfig(storage_backend="memory", default_tenant_id="tenant_cons")

    async with MemoryEngine(config=config) as engine:
        await engine.remember(
            content="User logged into dashboard from New York IP.",
            author_id="auth_svc",
            memory_type=MemoryCategory.EPISODIC,
        )
        await engine.remember(
            content="User updated dashboard preferences from New York IP.",
            author_id="auth_svc",
            memory_type=MemoryCategory.EPISODIC,
        )

        consolidated = await engine.consolidate()
        assert isinstance(consolidated, list)


@pytest.mark.asyncio
async def test_memory_engine_not_found_handling() -> None:
    """Verify appropriate exception is raised when inspecting missing memory."""
    config = MemoryConfig(storage_backend="memory")
    async with MemoryEngine(config=config) as engine:
        random_id = uuid4()
        with pytest.raises(MemoryNotFoundError):
            await engine.inspect(random_id)


def test_sync_memory_engine() -> None:
    """Verify synchronous wrapper operates cleanly without blocking or deadlocking."""
    config = MemoryConfig(storage_backend="memory", default_tenant_id="tenant_sync")

    with SyncMemoryEngine(config=config) as engine:
        # 1. Remember synchronously
        item = engine.remember(
            content="Synchronous memory ingestion works in dedicated thread loop.",
            author_id="sync_tester",
            memory_type=MemoryCategory.SEMANTIC,
            importance=0.8,
        )
        assert item.id is not None
        assert "Synchronous" in item.content

        # 2. Inspect synchronously
        inspection = engine.inspect(item.id)
        assert inspection.record.id == item.id

        # 3. Recall synchronously
        res = engine.recall(query="dedicated thread loop")
        assert len(res.results) >= 1
        assert res.results[0].item.id == item.id

        # 4. Stats synchronously
        stats = engine.stats()
        assert stats.total_memories == 1

        # 5. Update synchronously
        updated = engine.update(item.id, new_content="Synchronous wrapper updated content.")
        assert "updated" in updated.content

        # 6. Forget synchronously
        forgotten = engine.forget(item.id)
        assert forgotten is True
