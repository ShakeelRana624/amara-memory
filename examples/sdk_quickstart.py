"""AMARA Python SDK Quickstart Example.

Demonstrates remembering, recalling, consolidating, and reconstructing
grounded context using the developer-friendly asynchronous Python SDK.
"""

from __future__ import annotations

import asyncio

from amara.enums import MemoryCategory
from amara.sdk import MemoryConfig, MemoryEngine


async def main() -> None:
    print("--- 1. Initializing AMARA Cognitive Memory Engine ---")
    config = MemoryConfig(
        storage_backend="memory",
        default_tenant_id="acme_ai",
        default_namespace="agent_workspace",
        token_budget=1024,
    )

    async with MemoryEngine(config=config) as engine:
        print("\n--- 2. Ingesting Observations (remember) ---")
        item1 = await engine.remember(
            content="User prefers Python 3.12 with Pydantic v2 schemas and strict typing.",
            author_id="user_alice",
            memory_type=MemoryCategory.SEMANTIC,
            confidence=0.98,
            importance=0.85,
        )
        print(f"Stored Memory 1: ID={item1.id} | Status={item1.status.value}")

        item2 = await engine.remember(
            content="User requested PostgreSQL 16 with pgvector for the backend storage database.",
            author_id="user_alice",
            memory_type=MemoryCategory.SEMANTIC,
            confidence=0.95,
            importance=0.90,
        )
        print(f"Stored Memory 2: ID={item2.id} | Status={item2.status.value}")

        item3 = await engine.remember(
            content="Debugging session: Redis cache is running on port 6379 in production.",
            author_id="devops_agent",
            memory_type=MemoryCategory.EPISODIC,
            confidence=0.92,
            importance=0.60,
        )
        print(f"Stored Memory 3: ID={item3.id} | Status={item3.status.value}")

        print("\n--- 3. Hybrid Recall (recall) ---")
        search_result = await engine.recall(
            query="What database and python version does the user prefer?",
            top_k=5,
        )
        print(
            f"Retrieved {len(search_result.results)} candidates in {search_result.latency_ms:.2f}ms:"
        )
        for r in search_result.results:
            print(f"  - [{r.relevance_score:.2f}] {r.item.content}")

        print("\n--- 4. Grounded Context Reconstruction (reconstruct) ---")
        context = await engine.reconstruct(
            query="Summarize project requirements and preferences",
            budget=512,
        )
        print(f"Abstention Recommended: {context.abstention_recommended}")
        print(
            f"Tokens Used: {context.total_tokens_used} / Remaining Budget: {context.remaining_token_budget}"
        )
        print("\nFormatted Prompt Block:")
        print(context.formatted_context)

        print("\nCitations:")
        for cit in context.citations:
            print(f"  {cit.citation_tag} -> Memory {cit.memory_id} (Author: {cit.author_id})")

        print("\n--- 5. Cognitive Distribution Statistics (stats) ---")
        stats = await engine.stats()
        print(f"Total Memories: {stats.total_memories}")
        print(f"By Category: {stats.by_category}")
        print(f"By Status: {stats.by_status}")
        print(f"Average Confidence: {stats.average_confidence:.2f}")

        print("\n--- 6. Inspecting Memory Node (inspect) ---")
        inspection = await engine.inspect(memory_id=item1.id)
        print(f"Inspected Memory {inspection.record.id}:")
        print(f"  Content: {inspection.record.content}")
        print(f"  Author: {inspection.record.author_id}")
        print(f"  Version: {inspection.record.version}")


if __name__ == "__main__":
    asyncio.run(main())
