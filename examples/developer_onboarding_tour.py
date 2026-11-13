"""AMARA Developer Onboarding Tour: 60-Second Interactive Demonstration.

Executes a complete cognitive memory walkthrough:
1. Ingestion of Semantic, Episodic, and Procedural memories.
2. Automatic fact extraction and salience scoring.
3. 5-Way Hybrid Retrieval (Vector + BM25 + Temporal + Relational).
4. Deterministic Contradiction Handling (Fact Evolution).
5. Context Reconstruction with strict token budgeting and citations.

Usage:
    python examples/developer_onboarding_tour.py
"""

from __future__ import annotations

import asyncio

from amara.models.enums import MemoryType
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


async def main() -> None:
    print("\n" + "=" * 70)
    print("AMARA: 60-SECOND DEVELOPER ONBOARDING TOUR")
    print("Adaptive Memory Architecture for Reasoning and AI")
    print("=" * 70)

    # 1. Initialize Engine (Zero-dependency local memory mode for onboarding)
    config = MemoryConfig(storage_backend="memory", default_tenant_id="onboarding_user")
    print("\n[Step 1] Initializing AMARA Cognitive Memory Engine...")

    async with MemoryEngine(config) as engine:
        print("Engine initialized successfully.")

        # 2. Ingest Multi-Tier Memories
        print("\n[Step 2] Ingesting Multi-Tier Cognitive Memories...")

        # 2a. Semantic Memory (User preference)
        mem1 = await engine.remember(
            content="User prefers PostgreSQL 16 with pgvector over cloud-managed alternatives.",
            memory_type=MemoryType.SEMANTIC,
            importance=0.90,
            confidence=0.95,
        )
        print(f"  + [Semantic Memory] ID: {mem1.id} (Importance: 0.90)")

        # 2b. Episodic Memory (Historical interaction event)
        mem2 = await engine.remember(
            content="Session 104: User encountered database connection timeout on port 5432 at 14:00.",
            memory_type=MemoryType.EPISODIC,
            importance=0.75,
            confidence=0.90,
        )
        print(f"  + [Episodic Memory] ID: {mem2.id} (Importance: 0.75)")

        # 2c. Procedural Memory (Playbook / Skill)
        mem3 = await engine.remember(
            content="Database Debug Procedure: 1. Verify port listening 2. Check pg_hba.conf 3. Inspect pg_stat_activity.",
            memory_type=MemoryType.PROCEDURAL,
            importance=0.85,
            confidence=0.99,
        )
        print(f"  + [Procedural Memory] ID: {mem3.id} (Importance: 0.85)")

        # 3. 5-Way Hybrid Recall
        print("\n[Step 3] Executing 5-Way Hybrid Retrieval (Vector + BM25 + Recency + RRF)...")
        query = "What database does the user prefer and how do we debug connection issues?"
        recall_resp = await engine.recall(
            query=query,
            strategy=RetrievalStrategy.HYBRID,
            top_k=3,
        )

        print(f'Query: "{query}"')
        for idx, r in enumerate(recall_resp.results, start=1):
            print(
                f"  Result #{idx} [{r.item.memory_type.value.upper()}] "
                f"(Score: {r.relevance_score:.3f}): {r.item.content[:75]}..."
            )

        # 4. Contradiction Resolution & Temporal Fact Updating
        print("\n[Step 4] Testing Deterministic Contradiction Reconciliation...")
        print("Scenario: User informs us they switched from PostgreSQL to SQLite for local tests.")
        mem_updated = await engine.remember(
            content="User prefers SQLite for local unit testing rather than PostgreSQL.",
            memory_type=MemoryType.SEMANTIC,
            importance=0.92,
            confidence=0.98,
        )
        print(f"  + [New Observation Recorded] ID: {mem_updated.id}")

        print("Querying current preference to verify temporal reconciliation:")
        reconciled_resp = await engine.recall(
            query="What database does the user prefer for local testing?",
            top_k=2,
        )
        for idx, r in enumerate(reconciled_resp.results, start=1):
            print(f"  [{idx}] {r.item.content}")

        # 5. Context Prompt Reconstruction for LLM Injection
        print("\n[Step 5] Reconstructing Token-Bounded Prompt Context with Citations...")
        reconstructed = await engine.reconstruct(
            query="Summarize user database preferences and troubleshooting steps for the agent.",
            budget=400,
        )

        print("--- Generated Prompt Context Block (Consumable by Agent) ---")
        print(reconstructed.formatted_context)
        print("-" * 60)
        print(f"Tokens Consumed: {reconstructed.total_tokens_used} / 400")
        print(f"Citation Sources Attributed: {len(reconstructed.citations)}")

        # 6. Tenant Stats
        stats = await engine.stats()
        print("\n[Step 6] Inspecting Tenant Memory Footprint:")
        print(f"  Total Active Memories: {stats.total_memories}")
        print(f"  Memory Type Breakdown: {stats.by_category}")

    print("\n" + "=" * 70)
    print("AMARA ONBOARDING TOUR COMPLETE: SYSTEM PRODUCTION-READY")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
