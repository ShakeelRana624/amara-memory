"""Concurrency stress and race-condition tests for AMARA cognitive memory."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor

import pytest

from amara.enums import MemoryCategory
from amara.exceptions import ConcurrencyError
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine


@pytest.fixture
async def stress_engine() -> MemoryEngine:
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()
    return engine


@pytest.fixture
def sync_stress_engine() -> Generator[SyncMemoryEngine, None, None]:
    config = MemoryConfig(storage_backend="memory")
    engine = SyncMemoryEngine(config=config)
    yield engine
    engine.close()


# ===========================================================================
# 1. High-Throughput Multi-Tenant Concurrent Ingestion
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_multi_tenant_ingestion_no_crosstalk(
    stress_engine: MemoryEngine,
) -> None:
    """Stress test: 50 concurrent ingestion tasks across 10 distinct tenants."""
    tenants = [f"stress_tenant_{i}" for i in range(10)]
    items_per_tenant = 5

    async def ingest_task(tenant: str, idx: int) -> str:
        mem = await stress_engine.remember(
            content=f"Secret proposition {idx} exclusive to {tenant}",
            memory_type=MemoryCategory.SEMANTIC,
            tenant_id=tenant,
            namespace="load_test",
        )
        return str(mem.id)

    # Launch 50 concurrent writes
    tasks = []
    for t in tenants:
        for i in range(items_per_tenant):
            tasks.append(ingest_task(t, i))

    results = await asyncio.gather(*tasks)
    assert len(results) == 50

    # Verify each tenant has exactly 5 memories and zero cross-tenant contamination
    for t in tenants:
        stats = await stress_engine.stats(tenant_id=t, namespace="load_test")
        assert stats.total_memories == items_per_tenant

        # Recall should only return its own propositions
        rec = await stress_engine.recall(
            query="Secret proposition exclusive",
            tenant_id=t,
            namespace="load_test",
            top_k=20,
        )
        assert len(rec.results) == items_per_tenant
        for r in rec.results:
            assert t in r.item.content


# ===========================================================================
# 2. Optimistic Concurrency & Simultaneous Updates
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_updates_on_same_memory(stress_engine: MemoryEngine) -> None:
    """Verify concurrent updates to the same memory either serialize or raise ConcurrencyError."""
    # 1. Create initial memory
    mem = await stress_engine.remember(
        content="Initial configuration parameter: threads=4",
        tenant_id="tenant_concurrency",
    )

    # 2. Fire 10 simultaneous updates to the same record
    update_count = 10
    success_count = 0
    concurrency_errors = 0

    async def do_update(new_threads: int) -> None:
        nonlocal success_count, concurrency_errors
        try:
            await stress_engine.update(
                memory_id=mem.id,
                new_content=f"Updated configuration parameter: threads={new_threads}",
                tenant_id="tenant_concurrency",
            )
            success_count += 1
        except ConcurrencyError:
            concurrency_errors += 1

    await asyncio.gather(*[do_update(i + 5) for i in range(update_count)])

    # All operations must either succeed safely or fail with clean ConcurrencyError
    assert success_count + concurrency_errors == update_count
    assert success_count >= 1

    # Record must still be valid and intact
    final_mem = await stress_engine.inspect(mem.id, tenant_id="tenant_concurrency")
    assert final_mem is not None
    assert "threads=" in final_mem.record.content


# ===========================================================================
# 3. Concurrent Ingestion & Consolidation
# ===========================================================================


@pytest.mark.asyncio
async def test_concurrent_consolidation_and_ingestion(stress_engine: MemoryEngine) -> None:
    """Verify consolidation running in background while continuous ingestion proceeds."""
    # Seed preliminary related memories
    for i in range(5):
        await stress_engine.remember(
            content=f"User likes reading science fiction books, chapter {i}.",
            memory_type=MemoryCategory.EPISODIC,
            tenant_id="tenant_race",
            namespace="books",
        )

    async def ingester() -> None:
        for i in range(5, 10):
            await stress_engine.remember(
                content=f"User bought novel #{i} at the bookstore.",
                memory_type=MemoryCategory.EPISODIC,
                tenant_id="tenant_race",
                namespace="books",
            )
            await asyncio.sleep(0.01)

    async def consolidator() -> None:
        await asyncio.sleep(0.015)
        await stress_engine.consolidate(
            tenant_id="tenant_race",
            namespace="books",
        )

    # Run simultaneously
    await asyncio.gather(ingester(), consolidator())

    # System must remain healthy and queryable
    stats = await stress_engine.stats(tenant_id="tenant_race", namespace="books")
    assert stats.total_memories >= 5


# ===========================================================================
# 4. Multi-Threaded SyncMemoryEngine Stress Test
# ===========================================================================


def test_sync_memory_engine_multi_threaded_calls(
    sync_stress_engine: SyncMemoryEngine,
) -> None:
    """Verify ThreadPoolExecutor workers can safely invoke SyncMemoryEngine concurrently."""
    thread_count = 8
    calls_per_thread = 5

    def worker(worker_id: int) -> int:
        local_success = 0
        for i in range(calls_per_thread):
            mem = sync_stress_engine.remember(
                content=f"Sync record from thread {worker_id} iteration {i}",
                namespace="sync_stress",
            )
            if mem.id:
                local_success += 1
            # Perform recall
            res = sync_stress_engine.recall(
                query=f"thread {worker_id}",
                namespace="sync_stress",
                top_k=2,
            )
            if res.results:
                local_success += 1
        return local_success

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(worker, t) for t in range(thread_count)]
        results = [f.result() for f in futures]

    assert len(results) == thread_count
    # All worker iterations completed successfully without thread deadlocks
    for count in results:
        assert count == calls_per_thread * 2
