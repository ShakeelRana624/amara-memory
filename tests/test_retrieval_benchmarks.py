"""Benchmark evaluation suite measuring Recall@K, Precision@K, MRR, and latency."""

from __future__ import annotations

import datetime
import time
from uuid import UUID

import pytest

from amara.intelligence.pipeline import MemoryIngestionPipeline
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.retrieval.types import RetrievalStrategy
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def memory_repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


async def setup_benchmark_corpus(
    repo: InMemoryMemoryRepository,
) -> tuple[MemoryRetrievalEngine, dict[str, list[UUID]]]:
    """Ingest a controlled, deterministic corpus and return the engine and ground-truth mapping."""
    pipeline = MemoryIngestionPipeline(repository=repo)
    engine = MemoryRetrievalEngine(repository=repo)
    t0 = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=10)

    # Ingest 8 distinct facts
    doc1 = (
        await pipeline.ingest_text(
            content="PostgreSQL 16 relational database runs on port 5432.",
            tenant_id="bench-tenant",
            source_id="config-db",
            author_id="admin",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc2 = (
        await pipeline.ingest_text(
            content="Redis in-memory caching cluster runs on port 6379.",
            tenant_id="bench-tenant",
            source_id="config-cache",
            author_id="admin",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc3 = (
        await pipeline.ingest_text(
            content="Backend REST API web application runs on port 8000.",
            tenant_id="bench-tenant",
            source_id="config-api",
            author_id="admin",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc4 = (
        await pipeline.ingest_text(
            content="Authentication service uses JWT RS256 token encryption.",
            tenant_id="bench-tenant",
            source_id="config-auth",
            author_id="security",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc5 = (
        await pipeline.ingest_text(
            content="User Alice prefers dark mode theme in developer tools.",
            tenant_id="bench-tenant",
            source_id="prefs-alice",
            author_id="user-alice",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc6 = (
        await pipeline.ingest_text(
            content="User Bob prefers light mode theme in all interfaces.",
            tenant_id="bench-tenant",
            source_id="prefs-bob",
            author_id="user-bob",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc7 = (
        await pipeline.ingest_text(
            content="Deployment runbook: 1. run pytest 2. build docker 3. push image",
            tenant_id="bench-tenant",
            source_id="runbook-deploy",
            author_id="devops",
            asserted_at=t0,
        )
    ).stored_records[0]

    doc8 = (
        await pipeline.ingest_text(
            content="Kafka event streaming message broker runs on port 9092.",
            tenant_id="bench-tenant",
            source_id="config-kafka",
            author_id="infra",
            asserted_at=t0,
        )
    ).stored_records[0]

    # Ground truth mapping: Query -> List of relevant memory IDs
    ground_truth = {
        "What port does PostgreSQL database run on?": [doc1.id],
        "Redis cache port configuration": [doc2.id],
        "Which port is allocated for the backend web API?": [doc3.id],
        "How is authentication token encryption configured?": [doc4.id],
        "What theme does Alice prefer?": [doc5.id],
        "User preference for light mode": [doc6.id],
        "Steps to deploy the application image": [doc7.id],
        "Kafka message broker port": [doc8.id],
    }

    return engine, ground_truth


async def test_retrieval_benchmark_ir_metrics(
    memory_repo: InMemoryMemoryRepository,
) -> None:
    """Measure Recall@K, Precision@K, MRR, and latency on the controlled benchmark corpus."""
    engine, ground_truth = await setup_benchmark_corpus(memory_repo)
    k = 3

    recall_scores: list[float] = []
    precision_scores: list[float] = []
    reciprocal_ranks: list[float] = []
    latencies_ms: list[float] = []

    for query, relevant_ids in ground_truth.items():
        t_start = time.perf_counter()
        response = await engine.retrieve(
            query=query,
            tenant_id="bench-tenant",
            strategy=RetrievalStrategy.HYBRID,
            top_k=k,
        )
        latency = (time.perf_counter() - t_start) * 1000.0
        latencies_ms.append(latency)

        retrieved_ids = [r.memory_id for r in response.results]
        relevant_set = set(relevant_ids)
        retrieved_set = set(retrieved_ids[:k])

        # 1. Recall@K: |retrieved_K ∩ relevant| / |relevant|
        hits = len(retrieved_set.intersection(relevant_set))
        recall = hits / len(relevant_set) if relevant_set else 0.0
        recall_scores.append(recall)

        # 2. Precision@K: |retrieved_K ∩ relevant| / K
        precision = hits / k
        precision_scores.append(precision)

        # 3. Reciprocal Rank (RR): 1 / rank_of_first_relevant
        rr = 0.0
        for rank, rid in enumerate(retrieved_ids, start=1):
            if rid in relevant_set:
                rr = 1.0 / rank
                break
        reciprocal_ranks.append(rr)

    # Calculate aggregate metrics
    avg_recall = sum(recall_scores) / len(recall_scores)
    avg_precision = sum(precision_scores) / len(precision_scores)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    avg_latency = sum(latencies_ms) / len(latencies_ms)
    p95_latency = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]

    # Assert rigorous quantitative benchmarks
    assert avg_recall >= 0.85, f"Recall@{k} failed benchmark: {avg_recall:.3f} < 0.85"
    assert avg_precision >= 0.28, f"Precision@{k} failed benchmark: {avg_precision:.3f} < 0.28"
    assert mrr >= 0.85, f"MRR failed benchmark: {mrr:.3f} < 0.85"
    assert avg_latency < 50.0, f"Average latency too high: {avg_latency:.2f}ms"
    assert p95_latency < 100.0, f"P95 latency too high: {p95_latency:.2f}ms"


async def test_retrieval_strategy_latency_comparison(
    memory_repo: InMemoryMemoryRepository,
) -> None:
    """Benchmark and compare retrieval latency across independent strategies."""
    engine, _ = await setup_benchmark_corpus(memory_repo)
    q = "PostgreSQL database port configuration"

    strategies = [
        RetrievalStrategy.SEMANTIC,
        RetrievalStrategy.LEXICAL,
        RetrievalStrategy.TEMPORAL,
        RetrievalStrategy.HYBRID,
    ]

    for strat in strategies:
        res = await engine.retrieve(
            query=q,
            tenant_id="bench-tenant",
            strategy=strat,
            top_k=5,
        )
        assert res.strategy == strat
        assert res.latency_ms >= 0.0
        assert res.latency_ms < 100.0
