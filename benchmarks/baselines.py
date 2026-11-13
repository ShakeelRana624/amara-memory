"""Baselines for comparative empirical evaluation against AMARA cognitive architecture."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


@dataclass(frozen=True)
class BaselineResult:
    system_name: str
    query: str
    context_text: str
    retrieved_count: int
    tokens_consumed: int
    latency_ms: float
    abstention_flag: bool


class NoMemoryBaseline:
    """Baseline 1: Stateless model with zero external memory retrieval."""

    def __init__(self) -> None:
        self.name = "No-Memory (Stateless)"

    async def ingest(self, text: str, **kwargs: Any) -> None:
        pass

    async def retrieve_and_format(self, query: str, budget_tokens: int = 1024) -> BaselineResult:
        t0 = time.perf_counter()
        # Zero memory returned
        lat = (time.perf_counter() - t0) * 1000.0
        return BaselineResult(
            system_name=self.name,
            query=query,
            context_text="",
            retrieved_count=0,
            tokens_consumed=0,
            latency_ms=lat,
            abstention_flag=True,
        )


class ConversationSummaryBaseline:
    """Baseline 2: Monolithic sliding-window dialogue summary without indexing or decay."""

    def __init__(self, max_buffer_turns: int = 5) -> None:
        self.name = "Conversation-Summary (Naive Buffer)"
        self.max_buffer_turns = max_buffer_turns
        self.history: list[str] = []

    async def ingest(self, text: str, **kwargs: Any) -> None:
        self.history.append(text)
        if len(self.history) > self.max_buffer_turns:
            # Drop older turns
            self.history.pop(0)

    async def retrieve_and_format(self, query: str, budget_tokens: int = 1024) -> BaselineResult:
        t0 = time.perf_counter()
        summary = "Past Conversation Summary:\n" + "\n".join(f"- {h}" for h in self.history)
        tokens = int(len(summary.split()) * 1.3)
        lat = (time.perf_counter() - t0) * 1000.0
        return BaselineResult(
            system_name=self.name,
            query=query,
            context_text=summary if self.history else "",
            retrieved_count=len(self.history),
            tokens_consumed=tokens,
            latency_ms=lat,
            abstention_flag=len(self.history) == 0,
        )


class VectorRAGBaseline:
    """Baseline 3: Naive Vector RAG (Dense vector search only, no decay, no contradiction resolution)."""

    def __init__(self) -> None:
        self.name = "Vector RAG (Dense-Only Naive)"
        self.engine: MemoryEngine | None = None

    async def initialize(self) -> None:
        config = MemoryConfig(storage_backend="memory")
        self.engine = MemoryEngine(config=config)
        await self.engine.initialize()

    async def ingest(self, text: str, **kwargs: Any) -> None:
        assert self.engine is not None
        await self.engine.remember(content=text, memory_type=MemoryCategory.SEMANTIC)

    async def retrieve_and_format(self, query: str, budget_tokens: int = 1024) -> BaselineResult:
        assert self.engine is not None
        t0 = time.perf_counter()
        # Retrieve strictly with dense vector strategy
        recall_res = await self.engine.recall(
            query=query,
            strategy=RetrievalStrategy.SEMANTIC,
            top_k=5,
        )
        context_items = [r.item.content for r in recall_res.results]
        joined = "\n".join(f"- {item}" for item in context_items)
        tokens = int(len(joined.split()) * 1.3)
        lat = (time.perf_counter() - t0) * 1000.0
        return BaselineResult(
            system_name=self.name,
            query=query,
            context_text=joined,
            retrieved_count=len(context_items),
            tokens_consumed=tokens,
            latency_ms=lat,
            abstention_flag=len(context_items) == 0,
        )


class AMARAArchitecture:
    """AMARA Full Cognitive Framework (Hybrid retrieval, recency decay, contradiction handling, knapsack packing)."""

    def __init__(self) -> None:
        self.name = "AMARA Cognitive Framework (v0.1)"
        self.engine: MemoryEngine | None = None

    async def initialize(self) -> None:
        config = MemoryConfig(storage_backend="memory")
        self.engine = MemoryEngine(config=config)
        await self.engine.initialize()

    async def ingest(
        self,
        text: str,
        category: MemoryCategory | str = MemoryCategory.SEMANTIC,
        **kwargs: Any,
    ) -> None:
        assert self.engine is not None
        await self.engine.remember(content=text, memory_type=category, **kwargs)

    async def retrieve_and_format(self, query: str, budget_tokens: int = 1024) -> BaselineResult:
        assert self.engine is not None
        t0 = time.perf_counter()
        recon = await self.engine.reconstruct(
            query=query,
            budget=budget_tokens,
            strategy=RetrievalStrategy.HYBRID,
        )
        lat = (time.perf_counter() - t0) * 1000.0
        return BaselineResult(
            system_name=self.name,
            query=query,
            context_text=recon.formatted_context,
            retrieved_count=len(recon.citations),
            tokens_consumed=recon.total_tokens_used,
            latency_ms=lat,
            abstention_flag=recon.abstention_recommended,
        )
