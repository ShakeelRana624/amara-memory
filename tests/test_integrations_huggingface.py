"""Tests for AMARA Hugging Face Transformers integration."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from amara.enums import MemoryCategory
from amara.integrations.huggingface import AmaraTransformersWrapper
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
async def test_transformers_agenerate_with_mock_pipeline(async_engine: MemoryEngine) -> None:
    # 1. Ingest baseline fact
    await async_engine.remember(
        content="Primary cloud deployment zone is AWS us-east-1.",
        memory_type=MemoryCategory.SEMANTIC,
        namespace="hf_test_ws",
    )

    # 2. Mock Hugging Face pipeline callable
    def mock_pipeline(prompt: str, **kwargs: object) -> list[dict[str, str]]:
        return [{"generated_text": f"{prompt} Deployed in AWS us-east-1."}]

    wrapper = AmaraTransformersWrapper(
        engine=async_engine,
        pipeline=mock_pipeline,
        namespace="hf_test_ws",
        token_budget=512,
        auto_remember_turns=True,
    )

    # 3. Generate with context augmentation
    res = await wrapper.agenerate(prompt="Which AWS region are we using?")
    assert "us-east-1" in res.reconstructed_context
    assert len(res.citations) >= 1
    assert "Deployed in AWS us-east-1." in res.generated_text

    # 4. Verify auto_remember_turns stored the conversation
    stats = await async_engine.stats(namespace="hf_test_ws")
    assert stats.by_category.get("episodic", 0) >= 1


def test_transformers_sync_generate(sync_engine: SyncMemoryEngine) -> None:
    sync_engine.remember(
        content="Model batch size is 32 with fp16 precision.",
        memory_type=MemoryCategory.SEMANTIC,
        namespace="hf_sync_ws",
    )

    def mock_model(prompt: str, **kwargs: object) -> str:
        return "Configured batch size: 32."

    wrapper = AmaraTransformersWrapper(
        engine=sync_engine,
        model=mock_model,
        namespace="hf_sync_ws",
        token_budget=512,
    )

    res = wrapper.generate(prompt="What is the model batch size?")
    assert "batch size is 32" in res.reconstructed_context
    assert res.generated_text == "Configured batch size: 32."
    assert res.tokens_used > 0
