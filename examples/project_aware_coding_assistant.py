"""Project-Aware Coding Assistant Example using AMARA Cognitive Memory.

Demonstrates:
- Project repository architecture memory partition.
- Ingesting and recalling code standards, schema conventions, and runbooks.
- Grounding code generation in retrieved team rules to avoid outdated patterns.
- Multi-developer collaborative knowledge retention.
"""

from __future__ import annotations

import asyncio

from amara.integrations.generic_agent import AmaraAgentMemory
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


async def simulate_coding_assistant() -> None:
    print("=" * 70)
    print("AMARA Project-Aware Coding Assistant Walkthrough")
    print("=" * 70)

    # 1. Initialize AMARA cognitive engine
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    project_namespace = "repo_amara_core"
    coding_agent = AmaraAgentMemory(
        engine=engine,
        agent_id="code_assistant",
        namespace=project_namespace,
        default_budget_tokens=1536,
    )

    # 2. Teach the assistant project conventions
    print("\n[Step 1: Ingesting Project Architecture & Code Standards]")
    await coding_agent.alearn_fact(
        "AMARA Code Standard: All SQL operations must use SQLAlchemy 2.0 async style with select() and type annotations.",
        importance=0.95,
        metadata={"category": "coding_standard", "scope": "database"},
    )
    await coding_agent.alearn_fact(
        "AMARA Code Standard: Never use raw datetime.now() without datetime.UTC timezone awareness.",
        importance=0.90,
        metadata={"category": "coding_standard", "scope": "datetime"},
    )
    await coding_agent.alearn_procedure(
        "Runbook for adding database models: 1. Inherit from Base, 2. Add __tablename__, 3. Add to alembic env.py, 4. Run uv run alembic revision --autogenerate.",
        importance=0.98,
        metadata={"category": "runbook", "topic": "alembic_migrations"},
    )
    print("✓ Successfully ingested 3 project standards into namespace 'repo_amara_core'.")

    # 3. Developer asks for code implementation
    print("\n[Step 2: Developer asks to write a repository query]")
    dev_query = "Write a query function to retrieve active memory records by author ID."
    print(f"Developer Prompt: '{dev_query}'")

    # Coding assistant retrieves project conventions
    grounded_context = await coding_agent.abefore_step(query=dev_query)

    print("\n--- GROUNDED PROJECT CONTEXT INJECTED ---")
    print(grounded_context.formatted_context)
    print("----------------------------------------")

    # Simulated code generation respecting project rules
    generated_code = '''async def get_memories_by_author(
    session: AsyncSession,
    author_id: str,
) -> Sequence[MemoryRecordModel]:
    """Retrieve active records using SQLAlchemy 2.0 select() [REF-1]."""
    stmt = (
        select(MemoryRecordModel)
        .where(MemoryRecordModel.author_id == author_id)
        .where(MemoryRecordModel.status == LifecycleStatus.ACTIVE)
        .order_by(MemoryRecordModel.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()'''

    print(f"\nGenerated Code complying with standards:\n{generated_code}")

    # Persist interaction
    await coding_agent.aafter_step(
        user_message=dev_query,
        agent_response=generated_code,
        session_id="dev_task_query_author",
    )

    # 4. Check repository telemetry
    stats = await engine.stats(namespace=project_namespace)
    print("\nProject Memory Telemetry:")
    print(f"  • Total Project Rules & Records: {stats.total_memories}")
    print(f"  • Category Counts: {stats.by_category}")


if __name__ == "__main__":
    asyncio.run(simulate_coding_assistant())
