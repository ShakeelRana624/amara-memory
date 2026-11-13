"""Generic Python agent memory manager for AMARA.

Provides a clean, framework-agnostic cognitive memory facade for autonomous agent loops
(OpenAI, Anthropic, Gemini, local LLMs, and custom reasoning scripts):
- Pre-step grounded context reconstruction.
- Post-step episodic turn logging.
- Explicit semantic fact and procedural skill acquisition.
- Multi-session user memory isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine
from amara.sdk.types import MemoryItem


@dataclass(frozen=True)
class GroundedContext:
    """Retrieved epistemic context block with citation anchors."""

    formatted_context: str
    citations: tuple[dict[str, Any], ...]
    tokens_used: int
    abstention_recommended: bool

    def augment_prompt(self, user_prompt: str, template: str | None = None) -> str:
        """Compose user prompt with retrieved cognitive context."""
        if not self.formatted_context.strip():
            return user_prompt
        if template:
            return template.format(
                context=self.formatted_context,
                prompt=user_prompt,
            )
        return (
            f"=== VERIFIED COGNITIVE MEMORY ===\n"
            f"{self.formatted_context}\n"
            f"=== END MEMORY ===\n\n"
            f"User: {user_prompt}\n"
            f"Assistant:"
        )


class AmaraAgentMemory:
    """High-level cognitive memory manager for generic autonomous agents."""

    def __init__(
        self,
        engine: MemoryEngine | SyncMemoryEngine,
        agent_id: str = "amara_agent",
        namespace: str = "default",
        tenant_id: str | None = None,
        default_budget_tokens: int = 1536,
        default_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
    ) -> None:
        """Initialize generic agent memory wrapper.

        Args:
            engine: AMARA MemoryEngine (async) or SyncMemoryEngine (sync).
            agent_id: Identity label for the calling agent.
            namespace: Memory partition namespace.
            tenant_id: Optional tenant isolation scope.
            default_budget_tokens: Default token limit for context reconstruction.
            default_strategy: Retrieval strategy (hybrid, dense, lexical, etc.).
        """
        self.engine = engine
        self.agent_id = agent_id
        self.namespace = namespace
        self.tenant_id = tenant_id
        self.default_budget_tokens = default_budget_tokens
        self.default_strategy = default_strategy

    # -----------------------------------------------------------------------
    # Synchronous Operations (SyncMemoryEngine)
    # -----------------------------------------------------------------------

    def before_step(
        self,
        query: str,
        budget_tokens: int | None = None,
        namespace: str | None = None,
    ) -> GroundedContext:
        """Synchronously retrieve grounded context before agent reasoning."""
        if not isinstance(self.engine, SyncMemoryEngine):
            raise RuntimeError(
                "before_step() requires a SyncMemoryEngine. Use abefore_step() for async."
            )

        ns = namespace or self.namespace
        budget = budget_tokens or self.default_budget_tokens

        recon = self.engine.reconstruct(
            query=query,
            namespace=ns,
            budget=budget,
            strategy=self.default_strategy,
            tenant_id=self.tenant_id,
        )

        citations = tuple(
            {
                "citation_tag": c.citation_tag,
                "memory_id": str(c.memory_id),
                "source_id": c.source_id,
                "author_id": c.author_id,
                "snippet": c.snippet,
                "temporal_anchor": c.temporal_anchor,
            }
            for c in recon.citations
        )

        return GroundedContext(
            formatted_context=recon.formatted_context,
            citations=citations,
            tokens_used=recon.total_tokens_used,
            abstention_recommended=recon.abstention_recommended,
        )

    def after_step(
        self,
        user_message: str,
        agent_response: str,
        session_id: str | None = None,
        importance: float = 0.6,
        namespace: str | None = None,
    ) -> MemoryItem:
        """Synchronously persist turn interaction into episodic memory."""
        if not isinstance(self.engine, SyncMemoryEngine):
            raise RuntimeError(
                "after_step() requires a SyncMemoryEngine. Use aafter_step() for async."
            )

        ns = namespace or self.namespace
        content = f"User: {user_message}\nAgent: {agent_response}"

        return self.engine.remember(
            content=content,
            author_id=self.agent_id,
            memory_type=MemoryCategory.EPISODIC,
            importance=importance,
            namespace=ns,
            session_id=session_id,
            tenant_id=self.tenant_id,
        )

    def learn_fact(
        self,
        fact: str,
        confidence: float = 1.0,
        importance: float = 0.8,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Synchronously learn and record a persistent semantic fact."""
        if not isinstance(self.engine, SyncMemoryEngine):
            raise RuntimeError(
                "learn_fact() requires a SyncMemoryEngine. Use alearn_fact() for async."
            )

        ns = namespace or self.namespace
        return self.engine.remember(
            content=fact,
            author_id=self.agent_id,
            memory_type=MemoryCategory.SEMANTIC,
            confidence=confidence,
            importance=importance,
            namespace=ns,
            metadata=metadata,
            tenant_id=self.tenant_id,
        )

    def learn_procedure(
        self,
        instructions: str,
        importance: float = 0.9,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Synchronously learn a procedural skill or step-by-step runbook."""
        if not isinstance(self.engine, SyncMemoryEngine):
            raise RuntimeError(
                "learn_procedure() requires a SyncMemoryEngine. Use alearn_procedure() for async."
            )

        ns = namespace or self.namespace
        return self.engine.remember(
            content=instructions,
            author_id=self.agent_id,
            memory_type=MemoryCategory.PROCEDURAL,
            confidence=1.0,
            importance=importance,
            namespace=ns,
            metadata=metadata,
            tenant_id=self.tenant_id,
        )

    # -----------------------------------------------------------------------
    # Asynchronous Operations (MemoryEngine)
    # -----------------------------------------------------------------------

    async def abefore_step(
        self,
        query: str,
        budget_tokens: int | None = None,
        namespace: str | None = None,
    ) -> GroundedContext:
        """Asynchronously retrieve grounded context before agent reasoning."""
        ns = namespace or self.namespace
        budget = budget_tokens or self.default_budget_tokens

        if isinstance(self.engine, MemoryEngine):
            recon = await self.engine.reconstruct(
                query=query,
                namespace=ns,
                budget=budget,
                strategy=self.default_strategy,
                tenant_id=self.tenant_id,
            )
        else:
            recon = self.engine.reconstruct(
                query=query,
                namespace=ns,
                budget=budget,
                strategy=self.default_strategy,
                tenant_id=self.tenant_id,
            )

        citations = tuple(
            {
                "citation_tag": c.citation_tag,
                "memory_id": str(c.memory_id),
                "source_id": c.source_id,
                "author_id": c.author_id,
                "snippet": c.snippet,
                "temporal_anchor": c.temporal_anchor,
            }
            for c in recon.citations
        )

        return GroundedContext(
            formatted_context=recon.formatted_context,
            citations=citations,
            tokens_used=recon.total_tokens_used,
            abstention_recommended=recon.abstention_recommended,
        )

    async def aafter_step(
        self,
        user_message: str,
        agent_response: str,
        session_id: str | None = None,
        importance: float = 0.6,
        namespace: str | None = None,
    ) -> MemoryItem:
        """Asynchronously persist turn interaction into episodic memory."""
        ns = namespace or self.namespace
        content = f"User: {user_message}\nAgent: {agent_response}"

        if isinstance(self.engine, MemoryEngine):
            return await self.engine.remember(
                content=content,
                author_id=self.agent_id,
                memory_type=MemoryCategory.EPISODIC,
                importance=importance,
                namespace=ns,
                session_id=session_id,
                tenant_id=self.tenant_id,
            )
        return self.engine.remember(
            content=content,
            author_id=self.agent_id,
            memory_type=MemoryCategory.EPISODIC,
            importance=importance,
            namespace=ns,
            session_id=session_id,
            tenant_id=self.tenant_id,
        )

    async def alearn_fact(
        self,
        fact: str,
        confidence: float = 1.0,
        importance: float = 0.8,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Asynchronously learn and record a persistent semantic fact."""
        ns = namespace or self.namespace
        if isinstance(self.engine, MemoryEngine):
            return await self.engine.remember(
                content=fact,
                author_id=self.agent_id,
                memory_type=MemoryCategory.SEMANTIC,
                confidence=confidence,
                importance=importance,
                namespace=ns,
                metadata=metadata,
                tenant_id=self.tenant_id,
            )
        return self.engine.remember(
            content=fact,
            author_id=self.agent_id,
            memory_type=MemoryCategory.SEMANTIC,
            confidence=confidence,
            importance=importance,
            namespace=ns,
            metadata=metadata,
            tenant_id=self.tenant_id,
        )

    async def alearn_procedure(
        self,
        instructions: str,
        importance: float = 0.9,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """Asynchronously learn a procedural skill or step-by-step runbook."""
        ns = namespace or self.namespace
        if isinstance(self.engine, MemoryEngine):
            return await self.engine.remember(
                content=instructions,
                author_id=self.agent_id,
                memory_type=MemoryCategory.PROCEDURAL,
                confidence=1.0,
                importance=importance,
                namespace=ns,
                metadata=metadata,
                tenant_id=self.tenant_id,
            )
        return self.engine.remember(
            content=instructions,
            author_id=self.agent_id,
            memory_type=MemoryCategory.PROCEDURAL,
            confidence=1.0,
            importance=importance,
            namespace=ns,
            metadata=metadata,
            tenant_id=self.tenant_id,
        )

    async def aforget(self, memory_id: UUID | str, hard: bool = False) -> bool:
        """Asynchronously delete or tombstone a memory record."""
        target_id = UUID(str(memory_id))
        if isinstance(self.engine, MemoryEngine):
            return await self.engine.forget(
                memory_id=target_id,
                hard=hard,
                tenant_id=self.tenant_id,
            )
        return self.engine.forget(
            memory_id=target_id,
            hard=hard,
            tenant_id=self.tenant_id,
        )
