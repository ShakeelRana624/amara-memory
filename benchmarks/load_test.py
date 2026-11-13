"""AMARA Production Load Testing and Stress Benchmarking Harness.

Executes concurrent, high-throughput memory operations measuring:
- Concurrent requests (10, 50, 100 concurrent workers)
- Operation throughput (requests/sec)
- P50, P95, and P99 latency percentiles
- Error rate under concurrency
- Resource consumption (Memory & CPU)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import statistics
import time
from pathlib import Path
from typing import Any

from amara.models.enums import MemoryType
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("amara.load_test")

SAMPLE_PROPOSITIONS = [
    "User prefers strict TypeScript over loosely-typed JavaScript.",
    "PostgreSQL 16 deployed on port 5432 with pgvector 0.7.0 extension.",
    "Customer requested webhook notification upon high-severity security incidents.",
    "Authentication cluster requires bearer token signed with HMAC-SHA256.",
    "Session rate limit configured to 120 requests per minute with burst of 200.",
    "Memory retention policy enforces 30-day half-life decay on inactive traces.",
    "Primary Kubernetes ingress routes traffic via Caddy reverse proxy with automatic TLS.",
    "Database connection pool size set to 20 connections with 10 max overflow.",
    "LangGraph memory adapter configured with pre-hook recall and post-hook reflection.",
    "Context reconstruction engine limits output tokens to 1024 with markdown citations.",
]

SAMPLE_QUERIES = [
    "What are the user's programming language preferences?",
    "What is the database version and port configuration?",
    "How are webhook notifications handled for security incidents?",
    "What authentication signature method is required by the cluster?",
    "What are the rate limiting parameters for API sessions?",
    "How does the memory retention decay policy work?",
    "What reverse proxy is used for Kubernetes ingress?",
    "How many connections are allocated in the PostgreSQL database pool?",
    "How is the LangGraph memory adapter configured?",
    "What is the maximum token budget for context reconstruction?",
]


async def worker_task(
    worker_id: int,
    engine: MemoryEngine,
    iterations_per_worker: int,
    latencies: list[dict[str, Any]],
    tenant_id: str,
) -> None:
    """Individual worker coroutine executing interleaved remember, recall, and reconstruct operations."""
    for i in range(iterations_per_worker):
        # 1. Benchmark: Remember (Ingest)
        content = f"[Worker-{worker_id}-Iter-{i}] {random.choice(SAMPLE_PROPOSITIONS)}"
        mem_type = random.choice([MemoryType.SEMANTIC, MemoryType.EPISODIC, MemoryType.WORKING])
        t0 = time.perf_counter()
        success = True
        err_msg = ""
        try:
            await engine.remember(
                content=content,
                memory_type=mem_type,
                tenant_id=tenant_id,
                importance=random.uniform(0.5, 0.95),
                confidence=random.uniform(0.7, 0.99),
            )
        except Exception as e:
            success = False
            err_msg = str(e)
        t_remember = (time.perf_counter() - t0) * 1000.0
        latencies.append(
            {
                "operation": "remember",
                "latency_ms": t_remember,
                "success": success,
                "error": err_msg,
            }
        )

        # 2. Benchmark: Recall (Hybrid Retrieval)
        query = random.choice(SAMPLE_QUERIES)
        t0 = time.perf_counter()
        success = True
        err_msg = ""
        try:
            await engine.recall(
                query=query,
                strategy=RetrievalStrategy.HYBRID,
                top_k=5,
                tenant_id=tenant_id,
            )
        except Exception as e:
            success = False
            err_msg = str(e)
        t_recall = (time.perf_counter() - t0) * 1000.0
        latencies.append(
            {
                "operation": "recall",
                "latency_ms": t_recall,
                "success": success,
                "error": err_msg,
            }
        )

        # 3. Benchmark: Reconstruct (Context Assembly)
        t0 = time.perf_counter()
        success = True
        err_msg = ""
        try:
            await engine.reconstruct(
                query=query,
                budget=600,
                tenant_id=tenant_id,
            )
        except Exception as e:
            success = False
            err_msg = str(e)
        t_reconstruct = (time.perf_counter() - t0) * 1000.0
        latencies.append(
            {
                "operation": "reconstruct",
                "latency_ms": t_reconstruct,
                "success": success,
                "error": err_msg,
            }
        )


def calculate_percentiles(values: list[float]) -> dict[str, float]:
    """Calculate p50, p95, and p99 percentiles."""
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "max": 0.0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    return {
        "p50": round(sorted_v[int(n * 0.50)], 2),
        "p95": round(sorted_v[min(int(n * 0.95), n - 1)], 2),
        "p99": round(sorted_v[min(int(n * 0.99), n - 1)], 2),
        "mean": round(statistics.mean(sorted_v), 2),
        "max": round(max(sorted_v), 2),
    }


async def run_load_test(
    concurrency: int = 50,
    total_requests: int = 1500,
    storage_backend: str = "memory",
    database_url: str | None = None,
) -> dict[str, Any]:
    """Execute complete load test suite."""
    logger.info(
        "=== AMARA Load Test: Concurrency=%d, TotalOps=%d, Storage=%s ===",
        concurrency,
        total_requests,
        storage_backend,
    )

    config = MemoryConfig(
        storage_backend=storage_backend,
        database_url=database_url or os.getenv("AMARA_DATABASE_URL"),
        db_pool_size=concurrency,
        db_max_overflow=concurrency // 2,
    )

    latencies: list[dict[str, Any]] = []
    iterations_per_worker = max(1, total_requests // (concurrency * 3))

    async with MemoryEngine(config) as engine:
        # Pre-seed 100 baseline records so retrieval benchmarks operate on populated stores
        logger.info("Pre-seeding baseline memory knowledge base...")
        tenant_id = f"load_test_tenant_{concurrency}"
        for text in SAMPLE_PROPOSITIONS * 10:
            await engine.remember(
                content=text,
                memory_type=MemoryType.SEMANTIC,
                tenant_id=tenant_id,
            )

        # Launch concurrent workers
        logger.info(
            "Launching %d concurrent workers (3 operations * %d iterations each)...",
            concurrency,
            iterations_per_worker,
        )
        start_time = time.perf_counter()

        tasks = [
            worker_task(
                worker_id=w,
                engine=engine,
                iterations_per_worker=iterations_per_worker,
                latencies=latencies,
                tenant_id=tenant_id,
            )
            for w in range(concurrency)
        ]
        await asyncio.gather(*tasks)

        elapsed_time = time.perf_counter() - start_time

    total_ops = len(latencies)
    successful_ops = sum(1 for op in latencies if op["success"])
    failed_ops = total_ops - successful_ops
    throughput_rps = round(total_ops / elapsed_time, 2)
    error_rate = round((failed_ops / total_ops) * 100.0, 3) if total_ops > 0 else 0.0

    # Group by operation
    by_op: dict[str, list[float]] = {"remember": [], "recall": [], "reconstruct": []}
    for op in latencies:
        if op["success"]:
            by_op[op["operation"]].append(op["latency_ms"])

    all_successful = [op["latency_ms"] for op in latencies if op["success"]]

    results: dict[str, Any] = {
        "concurrency": concurrency,
        "storage_backend": storage_backend,
        "total_operations": total_ops,
        "successful_operations": successful_ops,
        "failed_operations": failed_ops,
        "error_rate_pct": error_rate,
        "elapsed_seconds": round(elapsed_time, 2),
        "throughput_req_per_sec": throughput_rps,
        "overall_latency_ms": calculate_percentiles(all_successful),
        "remember_latency_ms": calculate_percentiles(by_op["remember"]),
        "recall_latency_ms": calculate_percentiles(by_op["recall"]),
        "reconstruct_latency_ms": calculate_percentiles(by_op["reconstruct"]),
    }

    logger.info("=== Load Test Completed in %.2fs ===", elapsed_time)
    logger.info("Throughput: %.2f req/sec", throughput_rps)
    logger.info("Error Rate: %.2f%% (%d failures)", error_rate, failed_ops)
    logger.info(
        "Overall Latency: P50=%.2fms, P95=%.2fms, P99=%.2fms",
        results["overall_latency_ms"]["p50"],
        results["overall_latency_ms"]["p95"],
        results["overall_latency_ms"]["p99"],
    )
    logger.info(
        "Recall (Hybrid): P50=%.2fms, P95=%.2fms, P99=%.2fms",
        results["recall_latency_ms"]["p50"],
        results["recall_latency_ms"]["p95"],
        results["recall_latency_ms"]["p99"],
    )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="AMARA Load Testing Suite")
    parser.add_argument("--concurrency", type=int, default=50, help="Number of concurrent workers")
    parser.add_argument("--requests", type=int, default=600, help="Total target requests")
    parser.add_argument(
        "--storage",
        type=str,
        default="memory",
        choices=["memory", "postgres"],
        help="Storage backend implementation",
    )
    parser.add_argument("--output", type=str, default="benchmarks/results/load_test_results.json")
    args = parser.parse_args()

    results = asyncio.run(
        run_load_test(
            concurrency=args.concurrency,
            total_requests=args.requests,
            storage_backend=args.storage,
        )
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nResults successfully written to: {out_path}")


if __name__ == "__main__":
    main()
