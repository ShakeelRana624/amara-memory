"""LangGraph Assistant Example using AMARA Cognitive Memory Adapter.

Demonstrates:
- Composing a LangGraph-compatible state workflow with AMARA nodes.
- Pre-retrieval node injecting token-bounded context with citations.
- Agent reasoning node generating grounded outputs.
- Post-extraction node persisting episodic conversation turns.
- Multi-agent shared project knowledge retrieval.
"""

from __future__ import annotations

import asyncio
from typing import Any

from amara.enums import MemoryCategory
from amara.integrations.langgraph import AmaraLangGraphAdapter
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


async def simulate_langgraph_pipeline() -> None:
    print("=" * 70)
    print("AMARA LangGraph State Workflow Example")
    print("=" * 70)

    # 1. Initialize AMARA cognitive engine
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    # Pre-populate some initial knowledge
    await engine.remember(
        content="AMARA production databases require multi-AZ PostgreSQL 16 with pgvector and PgBouncer.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="tech_lead",
        namespace="dev_team_alpha",
    )
    await engine.remember(
        content="Deployment runbook: 1. Run alembic upgrade head, 2. Run vector index check, 3. Probe /api/v1/health.",
        memory_type=MemoryCategory.PROCEDURAL,
        author_id="devops_lead",
        namespace="dev_team_alpha",
    )
    print("✓ Preloaded foundational team knowledge into namespace 'dev_team_alpha'.")

    # 2. Instantiate AMARA LangGraph adapter
    adapter = AmaraLangGraphAdapter(
        engine=engine,
        default_namespace="dev_team_alpha",
    )

    # 3. Create reusable workflow nodes
    pre_retrieval = adapter.create_pre_retrieval_node(
        query_key="query",
        context_key="cognitive_context",
        budget_tokens=1024,
    )

    post_extraction = adapter.create_post_extraction_node(
        user_input_key="query",
        agent_output_key="response",
        extracted_memory_id_key="saved_memory_id",
    )

    memory_action = adapter.create_memory_action_node(
        action_key="memory_action",
        result_key="action_result",
    )

    # Simple simulated reasoning node
    async def reasoning_node(state: dict[str, Any]) -> dict[str, Any]:
        query = state["query"]
        context = state.get("cognitive_context", "")

        print(f"\n[Reasoning Node] Processing Query: '{query}'")
        print(f"[Reasoning Node] Grounded Context Injected:\n{context}")

        response = (
            "According to team standards [REF-1], our database requires PostgreSQL 16 "
            "with pgvector and PgBouncer in transaction pooling mode. "
            "Follow the deployment runbook: alembic migrations first, then health probes."
        )
        return {"response": response}

    # 4. Execute Workflow Turn 1: Developer query
    print("\n--- TURN 1: Developer asks for architecture guidelines ---")
    state_1: dict[str, Any] = {
        "query": "What are our database requirements and deployment steps?",
    }

    # Step A: Pre-retrieval
    pre_out = await pre_retrieval(state_1)
    state_1.update(pre_out)

    # Step B: Reasoning
    reasoning_out = await reasoning_node(state_1)
    state_1.update(reasoning_out)

    # Step C: Post-extraction
    post_out = await post_extraction(state_1)
    state_1.update(post_out)

    print(f"\nAssistant Response:\n{state_1['response']}")
    print(f"Turn Persisted in AMARA: memory_id={state_1['saved_memory_id']}")

    # 5. Execute Workflow Turn 2: Explicit memory action (Pinning a rule)
    print("\n--- TURN 2: Explicit Memory Action (Pin New Rule) ---")
    state_2: dict[str, Any] = {
        "memory_action": {
            "action": "remember",
            "content": "All API endpoints must return X-Request-ID headers for tracing.",
            "memory_type": "semantic",
            "confidence": 1.0,
            "importance": 0.95,
        }
    }
    action_out = await memory_action(state_2)
    state_2.update(action_out)
    print(f"Action Result: {state_2['action_result']}")

    # Verify memory is accessible in next query
    recall_check = await engine.recall(
        query="tracing headers requirements",
        namespace="dev_team_alpha",
    )
    print("\nImmediate Recall Verification:")
    for r in recall_check.results:
        print(f"  • Conf: {r.confidence:.2f} | {r.item.content}")


if __name__ == "__main__":
    asyncio.run(simulate_langgraph_pipeline())
