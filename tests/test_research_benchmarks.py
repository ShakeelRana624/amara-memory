"""Automated regression tests for research evaluation benchmarks."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

base_dir = Path(__file__).resolve().parent.parent / "benchmarks"
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from ablation_study import AblationHarness  # noqa: E402
from run_benchmarks import run_locomo_eval, run_long_mem_eval  # noqa: E402


@pytest.mark.asyncio
async def test_long_mem_eval_benchmark_accuracy() -> None:
    dataset_path = base_dir / "datasets" / "long_mem_eval_tasks.json"
    results = await run_long_mem_eval(dataset_path)

    # AMARA must achieve >= 95% factual recall on LongMemEval tasks
    amara_stats = results["AMARA-v0.1"]
    assert amara_stats["factual_accuracy"] >= 0.95
    assert amara_stats["avg_latency_ms"] < 100.0  # sub-100ms budget


@pytest.mark.asyncio
async def test_locomo_knowledge_update_accuracy() -> None:
    dataset_path = base_dir / "datasets" / "locomo_tasks.json"
    results = await run_locomo_eval(dataset_path)

    # AMARA update accuracy must substantially outperform naive Vector-RAG
    amara_update_acc = results["AMARA-v0.1"]["update_accuracy"]
    vec_rag_update_acc = results["Vector-RAG"]["update_accuracy"]

    assert amara_update_acc > vec_rag_update_acc
    assert amara_update_acc >= 0.90


@pytest.mark.asyncio
async def test_ablation_subsystem_contributions() -> None:
    harness = AblationHarness(random_seed=42)
    sample_events = [
        "Sarah lives in Seattle, WA as of 2026-01-01.",
        "Sarah relocated to Austin, Texas on 2026-06-01.",
    ]
    sample_queries = [
        {"query": "Where does Sarah currently live?", "expected": ["Austin, Texas"]},
    ]

    full = await harness.run_full_amara(sample_events, sample_queries)
    wo_temp = await harness.run_wo_temporal(sample_events, sample_queries)
    wo_contra = await harness.run_wo_contradiction(sample_events, sample_queries)

    # Full system must beat ablations in temporal and update accuracy
    assert full.temporal_accuracy > wo_temp.temporal_accuracy
    assert full.update_accuracy > wo_contra.update_accuracy
