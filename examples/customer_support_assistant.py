"""Customer Support Assistant Example using AMARA Cognitive Memory.

Demonstrates:
- Customer account SLA tracking and historical context.
- Grounding support answers in verified policy rules and incident runbooks.
- Generating citation-anchored customer responses.
- Updating customer tickets in memory across support interactions.
"""

from __future__ import annotations

import asyncio

from amara.integrations.generic_agent import AmaraAgentMemory
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine


async def simulate_support_assistant() -> None:
    print("=" * 70)
    print("AMARA Customer Support Assistant Walkthrough")
    print("=" * 70)

    # 1. Initialize AMARA cognitive engine
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()

    customer_id = "cust_enterprise_8041"
    support_agent = AmaraAgentMemory(
        engine=engine,
        agent_id="support_agent",
        namespace=customer_id,
        default_budget_tokens=1536,
    )

    # 2. Ingest customer account SLAs, history, and support policies
    print("\n[Step 1: Ingesting Customer Profile & SLA Guarantees]")
    await support_agent.alearn_fact(
        "Account cust_enterprise_8041 is on Enterprise Platinum SLA with 99.99% uptime guarantee and 15-minute response SLA.",
        importance=0.98,
        metadata={"category": "contract", "tier": "platinum"},
    )
    await support_agent.alearn_fact(
        "Customer primary technical contact is Alex Chen (alex@globex.io). Preferred notification channel is Slack webhook.",
        importance=0.90,
        metadata={"category": "contacts"},
    )
    await support_agent.alearn_procedure(
        "Runbook for 504 Gateway Timeout incidents: 1. Inspect PgBouncer pool saturation, 2. Check read replica lag, 3. Scale pool size to 50 connections.",
        importance=0.95,
        metadata={"category": "incident_runbook", "error_code": "504"},
    )
    print("✓ Successfully recorded customer SLA and troubleshooting runbook.")

    # 3. Customer submits an incident query
    print("\n[Step 2: Customer reports a production outage]")
    customer_ticket = "URGENT: Our dashboard is throwing 504 Gateway Timeout on memory search queries. What should we do?"
    print(f"Customer Message: '{customer_ticket}'")

    # Assistant reconstructs context
    grounded_context = await support_agent.abefore_step(query=customer_ticket)

    print("\n--- GROUNDED CUSTOMER & RUNBOOK CONTEXT ---")
    print(grounded_context.formatted_context)
    print("------------------------------------------")

    # Assistant generates grounded, audited support response
    support_reply = (
        "Hello Alex [REF-2],\n\n"
        "Thank you for reaching out. Under your Enterprise Platinum SLA [REF-1], "
        "our team is actively triaging your 504 Gateway Timeout incident.\n\n"
        "Immediate Remediation Steps [REF-3]:\n"
        "1. Check PgBouncer connection pool saturation on port 6432.\n"
        "2. Verify PostgreSQL read replica replication lag.\n"
        "3. Temporarily increase PgBouncer pool size to 50 connections.\n\n"
        "We are monitoring your cluster and will post real-time updates directly "
        "to your team's Slack webhook [REF-2]."
    )

    print(f"\nAssistant Response Sent to Customer:\n{support_reply}")

    # Persist support interaction
    await support_agent.aafter_step(
        user_message=customer_ticket,
        agent_response=support_reply,
        session_id="ticket_inc_77492",
    )

    # 4. Check memory telemetry
    stats = await engine.stats(namespace=customer_id)
    print("\nCustomer Knowledge Profile:")
    print(f"  • Total Propositions: {stats.total_memories}")
    print(f"  • Average Epistemic Certainty: {stats.average_confidence * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(simulate_support_assistant())
