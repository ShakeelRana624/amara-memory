"""Failure recovery, edge-case resilience, and graceful degradation tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from amara.exceptions import StorageError
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


@pytest.fixture
async def resilient_engine() -> MemoryEngine:
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()
    return engine


# ===========================================================================
# 1. Storage Disconnection & Rollback Resilience
# ===========================================================================


@pytest.mark.asyncio
async def test_storage_connection_failure_handling(resilient_engine: MemoryEngine) -> None:
    """Verify that a storage failure during remember/recall raises StorageError cleanly."""
    assert resilient_engine._repository is not None

    # Mock repository failure on store
    with patch.object(
        resilient_engine._repository, "store", side_effect=StorageError("Database connection lost")
    ):
        with pytest.raises(StorageError) as exc_info:
            await resilient_engine.remember(
                content="Will fail due to simulated database drop",
                tenant_id="tenant_fail",
            )
        assert "Database connection lost" in str(exc_info.value)

    # After recovery, engine must still function
    recovered_mem = await resilient_engine.remember(
        content="Engine recovered and storing properly",
        tenant_id="tenant_fail",
    )
    assert recovered_mem.id is not None


# ===========================================================================
# 2. Corrupted & Edge-Case Input Resilience
# ===========================================================================


@pytest.mark.asyncio
async def test_empty_and_whitespace_query_resilience(resilient_engine: MemoryEngine) -> None:
    """Verify search and context reconstruction handle empty, whitespace, and special characters."""
    # Ingest baseline
    await resilient_engine.remember(
        content="Standard operating fact",
        tenant_id="tenant_empty_test",
    )

    # 1. Empty query
    empty_recall = await resilient_engine.recall(
        query="",
        tenant_id="tenant_empty_test",
    )
    assert isinstance(empty_recall.results, (list, tuple))

    empty_reconstruct = await resilient_engine.reconstruct(
        query="",
        tenant_id="tenant_empty_test",
    )
    assert empty_reconstruct.total_tokens_used >= 0

    # 2. Whitespace and non-printable control characters
    ws_recall = await resilient_engine.recall(
        query="   \t\n\r  ",
        tenant_id="tenant_empty_test",
    )
    assert isinstance(ws_recall.results, (list, tuple))

    # 3. Only stopwords
    stopwords_recall = await resilient_engine.recall(
        query="and the is of in on at to a an",
        tenant_id="tenant_empty_test",
    )
    assert isinstance(stopwords_recall.results, (list, tuple))


@pytest.mark.asyncio
async def test_extremely_tight_token_budget_packing(resilient_engine: MemoryEngine) -> None:
    """Verify context reconstruction with budget smaller than a single proposition."""
    await resilient_engine.remember(
        content="A lengthy description of complex technical architecture specifications.",
        tenant_id="tenant_tight_budget",
    )

    # Budget of only 2 tokens (smaller than single memory header)
    tight_ctx = await resilient_engine.reconstruct(
        query="technical architecture",
        budget=2,
        tenant_id="tenant_tight_budget",
    )
    # Must not crash, should gracefully produce prompt with minimal tokens
    assert tight_ctx.total_tokens_used <= 50  # header minimum
    assert isinstance(tight_ctx.formatted_context, str)


# ===========================================================================
# 3. Abstention on Low-Confidence or Irrelevant Queries
# ===========================================================================


@pytest.mark.asyncio
async def test_abstention_recommendation_on_irrelevant_query(
    resilient_engine: MemoryEngine,
) -> None:
    """Verify abstention flag is recommended when query relevance falls below threshold."""
    await resilient_engine.remember(
        content="Company standard database is PostgreSQL 16.",
        tenant_id="tenant_abstain",
    )

    # Query completely unrelated to stored facts
    unrelated_ctx = await resilient_engine.reconstruct(
        query="What is the average flight speed of an unladen European swallow?",
        tenant_id="tenant_abstain",
    )
    # When zero relevant evidence is found, abstention must be recommended
    assert unrelated_ctx.abstention_recommended is True
    assert "Insufficient evidence" in str(unrelated_ctx.abstention_reason)


# ===========================================================================
# 4. Graceful Degradation on Provider Failures
# ===========================================================================


@pytest.mark.asyncio
async def test_provider_fallback_to_rule_based_extraction(
    resilient_engine: MemoryEngine,
) -> None:
    """Verify pipeline gracefully falls back to rule-based extractors on external provider crash."""
    assert resilient_engine._ingestion_pipeline is not None
    pipeline = resilient_engine._ingestion_pipeline

    # Mock remote intelligence provider failure
    with patch.object(
        pipeline.intelligence_provider,
        "extract_all",
        side_effect=RuntimeError("External LLM Provider Rate-Limited / Network Error"),
    ):
        # Ingestion should NOT fail; fallback to deterministic rule-based extractor
        mem = await resilient_engine.remember(
            content="Alice was promoted to VP of Engineering on 2026-05-01.",
            tenant_id="tenant_fallback",
        )
        assert mem.id is not None
        assert "Alice" in mem.content
        # Ingestion should NOT fail; fallback to deterministic rule-based extractor
        mem = await resilient_engine.remember(
            content="Alice was promoted to VP of Engineering on 2026-05-01.",
            tenant_id="tenant_fallback",
        )
        assert mem.id is not None
        assert "Alice" in mem.content
