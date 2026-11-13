"""Multi-Session Chatbot Example using AMARA Cognitive Memory.

Demonstrates:
- Epistemic tracking across distinct user conversation sessions.
- User preference and fact retention.
- Automated temporal contradiction handling (moving from Seattle to Austin).
- Token-bounded prompt context reconstruction with verifiable citations.
"""

from __future__ import annotations

import asyncio

from amara.integrations.generic_agent import AmaraAgentMemory
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


async def simulate_chatbot() -> None:
    print("=" * 70)
    print("AMARA Multi-Session Chatbot Walkthrough")
    print("=" * 70)

    # 1. Initialize AMARA cognitive engine
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    # Create agent memory manager
    user_id = "user_sarah_902"
    agent_memory = AmaraAgentMemory(
        engine=engine,
        agent_id="travel_assistant",
        namespace=user_id,
        default_budget_tokens=1024,
    )

    # -----------------------------------------------------------------------
    # SESSION 1 (Initial Setup)
    # -----------------------------------------------------------------------
    print("\n[SESSION 1: Initial User Introduction]")
    session_1 = "sess_october_01"

    # User intro message
    user_msg_1 = (
        "Hi! My name is Sarah. I currently live in Seattle, WA. "
        "I am a backend engineer working with PostgreSQL and Python."
    )
    print(f"User: {user_msg_1}")

    # Agent checks context before answering (empty on first turn)
    await agent_memory.abefore_step(query=user_msg_1)
    agent_resp_1 = (
        "Nice to meet you, Sarah! I've noted that you're based in Seattle "
        "and work as a Python and PostgreSQL backend engineer."
    )
    print(f"Assistant: {agent_resp_1}")

    # After step: Persist interaction in AMARA
    await agent_memory.aafter_step(user_msg_1, agent_resp_1, session_id=session_1)

    # Also extract structured semantic knowledge
    await agent_memory.alearn_fact("Sarah lives in Seattle, WA.", importance=0.85)
    await agent_memory.alearn_fact(
        "Sarah is a backend engineer specializing in Python and PostgreSQL.", importance=0.9
    )
    print("✓ Persisted Session 1 observations and semantic propositions.")

    # -----------------------------------------------------------------------
    # SESSION 2 (Relocation & Infrastructure Update)
    # -----------------------------------------------------------------------
    print("\n[SESSION 2: Relocation & Preference Change]")
    session_2 = "sess_november_12"

    user_msg_2 = (
        "Quick update: I have officially moved from Seattle to Austin, Texas! "
        "Also, our database stack now strictly requires PgBouncer connection pooling."
    )
    print(f"User: {user_msg_2}")

    # Agent checks prior memory
    context_2 = await agent_memory.abefore_step(query=user_msg_2)
    print(f"Grounded Memory Injected:\n{context_2.formatted_context}\n")

    agent_resp_2 = (
        "Congratulations on the move to Austin, Texas! I've updated your location "
        "from Seattle to Austin and noted your requirement for PgBouncer connection pooling."
    )
    print(f"Assistant: {agent_resp_2}")

    # After step: Persist interaction and supersede location
    await agent_memory.aafter_step(user_msg_2, agent_resp_2, session_id=session_2)
    await agent_memory.alearn_fact("Sarah lives in Austin, Texas.", importance=0.95)
    await agent_memory.alearn_fact(
        "Database stack requires PgBouncer connection pooling.", importance=0.9
    )
    print("✓ Persisted Session 2 updates. Austin supersedes Seattle.")

    # -----------------------------------------------------------------------
    # SESSION 3 (Complex Recall & Temporal Verification)
    # -----------------------------------------------------------------------
    print("\n[SESSION 3: Recall Verification across Sessions]")

    user_msg_3 = "Where do I currently live, and what is my database connection setup?"
    print(f"User: {user_msg_3}")

    # Agent reconstructs context from AMARA
    context_3 = await agent_memory.abefore_step(query=user_msg_3, budget_tokens=1024)

    print("\n--- RECONSTRUCTED COGNITIVE CONTEXT (Knapsack Packed with Citations) ---")
    print(context_3.formatted_context)
    print("-------------------------------------------------------------------------")
    print(
        f"Tokens Used: {context_3.tokens_used} | Abstention Recommended: {context_3.abstention_recommended}"
    )
    print(f"Verifiable Citations ({len(context_3.citations)}):")
    for cit in context_3.citations:
        print(f"  • {cit['citation_tag']}: {cit['snippet']} (Anchor: {cit['temporal_anchor']})")

    # Formulate grounded response
    agent_resp_3 = (
        "Based on your profile [REF-1], you currently live in Austin, Texas "
        "(having relocated from Seattle). Your database setup requires PostgreSQL "
        "with PgBouncer connection pooling [REF-2]."
    )
    print(f"\nAssistant: {agent_resp_3}")

    # Telemetry inspection
    stats = await engine.stats(namespace=user_id)
    print(f"\nTotal Memories for {user_id}: {stats.total_memories}")
    print(f"Category Distribution: {stats.by_category}")
    print(f"Epistemic Status: {stats.by_status}")


if __name__ == "__main__":
    asyncio.run(simulate_chatbot())
