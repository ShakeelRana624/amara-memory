"""LangGraph cognitive memory adapter for AMARA.

Provides reusable, framework-agnostic node factories for LangGraph StateGraph architectures:
- Before-agent token-bounded context retrieval with verifiable citations.
- After-agent episodic memory extraction and proposition persistence.
- Explicit memory updates, pin actions, and deletions.
- Multi-agent shared project knowledge partitions.

Does not tightly couple to LangGraph state internals; operates on standard dict or
Pydantic state schemas via duck-typing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.engine import MemoryEngine
from amara.sdk.sync import SyncMemoryEngine


class AmaraLangGraphAdapter:
    """Configurable adapter providing LangGraph-compatible state transformation nodes."""

    def __init__(
        self,
        engine: MemoryEngine | SyncMemoryEngine,
        default_namespace: str = "default",
        default_tenant: str | None = None,
    ) -> None:
        """Initialize the LangGraph memory adapter.

        Args:
            engine: AMARA MemoryEngine (async) or SyncMemoryEngine (thread-isolated sync).
            default_namespace: Default memory namespace / partition.
            default_tenant: Optional tenant ID boundary.
        """
        self.engine = engine
        self.default_namespace = default_namespace
        self.default_tenant = default_tenant

    # -----------------------------------------------------------------------
    # 1. Before-Agent Context Retrieval Node
    # -----------------------------------------------------------------------

    def create_pre_retrieval_node(
        self,
        query_key: str = "query",
        context_key: str = "cognitive_context",
        citations_key: str = "citations",
        budget_tokens: int = 2048,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        namespace_key: str | None = None,
    ) -> Callable[[dict[str, Any]], Any]:
        """Create a pre-execution node that reconstructs token-bounded context."""

        async def _async_pre_retrieval(state: dict[str, Any]) -> dict[str, Any]:
            query = state.get(query_key, "")
            if not query:
                return {context_key: "", citations_key: []}

            ns = (
                state.get(namespace_key, self.default_namespace)
                if namespace_key
                else self.default_namespace
            )

            # Reconstruct context via engine
            if isinstance(self.engine, SyncMemoryEngine):
                recon = self.engine.reconstruct(
                    query=query,
                    namespace=ns,
                    budget=budget_tokens,
                    strategy=strategy,
                    tenant_id=self.default_tenant,
                )
            else:
                recon = await self.engine.reconstruct(
                    query=query,
                    namespace=ns,
                    budget=budget_tokens,
                    strategy=strategy,
                    tenant_id=self.default_tenant,
                )

            citations_data = [
                {
                    "citation_tag": c.citation_tag,
                    "memory_id": str(c.memory_id),
                    "source_id": c.source_id,
                    "author_id": c.author_id,
                    "snippet": c.snippet,
                    "temporal_anchor": c.temporal_anchor,
                }
                for c in recon.citations
            ]

            return {
                context_key: recon.formatted_context,
                citations_key: citations_data,
                f"{context_key}_tokens_used": recon.total_tokens_used,
                f"{context_key}_abstention_recommended": recon.abstention_recommended,
            }

        def _sync_pre_retrieval(state: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(self.engine, SyncMemoryEngine):
                raise RuntimeError("Sync pre-retrieval node requires a SyncMemoryEngine instance.")
            query = state.get(query_key, "")
            if not query:
                return {context_key: "", citations_key: []}

            ns = (
                state.get(namespace_key, self.default_namespace)
                if namespace_key
                else self.default_namespace
            )

            recon = self.engine.reconstruct(
                query=query,
                namespace=ns,
                budget=budget_tokens,
                strategy=strategy,
                tenant_id=self.default_tenant,
            )

            citations_data = [
                {
                    "citation_tag": c.citation_tag,
                    "memory_id": str(c.memory_id),
                    "source_id": c.source_id,
                    "author_id": c.author_id,
                    "snippet": c.snippet,
                    "temporal_anchor": c.temporal_anchor,
                }
                for c in recon.citations
            ]

            return {
                context_key: recon.formatted_context,
                citations_key: citations_data,
                f"{context_key}_tokens_used": recon.total_tokens_used,
                f"{context_key}_abstention_recommended": recon.abstention_recommended,
            }

        if isinstance(self.engine, SyncMemoryEngine):
            return _sync_pre_retrieval
        return _async_pre_retrieval

    # -----------------------------------------------------------------------
    # 2. After-Agent Memory Extraction Node
    # -----------------------------------------------------------------------

    def create_post_extraction_node(
        self,
        user_input_key: str = "query",
        agent_output_key: str = "response",
        extracted_memory_id_key: str = "extracted_memory_id",
        memory_type: MemoryCategory = MemoryCategory.EPISODIC,
        importance: float = 0.6,
        confidence: float = 0.95,
        namespace_key: str | None = None,
        author_id: str = "langgraph_agent",
    ) -> Callable[[dict[str, Any]], Any]:
        """Create a post-execution node that ingests turn interactions into AMARA."""

        async def _async_post_extraction(state: dict[str, Any]) -> dict[str, Any]:
            user_msg = state.get(user_input_key, "")
            agent_msg = state.get(agent_output_key, "")
            if not agent_msg and not user_msg:
                return {extracted_memory_id_key: None}

            content = f"User Turn: {user_msg}\nAgent Response: {agent_msg}".strip()
            ns = (
                state.get(namespace_key, self.default_namespace)
                if namespace_key
                else self.default_namespace
            )

            if isinstance(self.engine, SyncMemoryEngine):
                item = self.engine.remember(
                    content=content,
                    author_id=author_id,
                    memory_type=memory_type,
                    confidence=confidence,
                    importance=importance,
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )
            else:
                item = await self.engine.remember(
                    content=content,
                    author_id=author_id,
                    memory_type=memory_type,
                    confidence=confidence,
                    importance=importance,
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )

            return {extracted_memory_id_key: str(item.id)}

        def _sync_post_extraction(state: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(self.engine, SyncMemoryEngine):
                raise RuntimeError(
                    "Sync post-extraction node requires a SyncMemoryEngine instance."
                )
            user_msg = state.get(user_input_key, "")
            agent_msg = state.get(agent_output_key, "")
            if not agent_msg and not user_msg:
                return {extracted_memory_id_key: None}

            content = f"User Turn: {user_msg}\nAgent Response: {agent_msg}".strip()
            ns = (
                state.get(namespace_key, self.default_namespace)
                if namespace_key
                else self.default_namespace
            )

            item = self.engine.remember(
                content=content,
                author_id=author_id,
                memory_type=memory_type,
                confidence=confidence,
                importance=importance,
                namespace=ns,
                tenant_id=self.default_tenant,
            )
            return {extracted_memory_id_key: str(item.id)}

        if isinstance(self.engine, SyncMemoryEngine):
            return _sync_post_extraction
        return _async_post_extraction

    # -----------------------------------------------------------------------
    # 3. Explicit Memory Update Node
    # -----------------------------------------------------------------------

    def create_memory_action_node(
        self,
        action_key: str = "memory_action",
        result_key: str = "memory_action_result",
    ) -> Callable[[dict[str, Any]], Any]:
        """Create a node for handling explicit commands (update, forget, pin, remember)."""

        async def _async_action(state: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(self.engine, MemoryEngine):
                raise RuntimeError("Async memory action node requires an async MemoryEngine.")
            engine = self.engine
            action_data = state.get(action_key)
            if not action_data or not isinstance(action_data, dict):
                return {result_key: {"status": "skipped", "reason": "no_action"}}

            action_type = action_data.get("action", "").lower()
            memory_id_str = action_data.get("memory_id")
            memory_id = UUID(memory_id_str) if memory_id_str else None

            if action_type == "remember":
                content = action_data.get("content", "")
                cat = action_data.get("memory_type", MemoryCategory.SEMANTIC)
                conf = float(action_data.get("confidence", 1.0))
                imp = float(action_data.get("importance", 0.8))
                ns = action_data.get("namespace", self.default_namespace)

                res = await engine.remember(
                    content=content,
                    memory_type=cat,
                    confidence=conf,
                    importance=imp,
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )
                return {result_key: {"status": "remembered", "memory_id": str(res.id)}}

            if action_type == "update" and memory_id:
                new_content = action_data.get("content")
                meta = action_data.get("metadata")
                res = await engine.update(
                    memory_id=memory_id,
                    new_content=new_content,
                    metadata_updates=meta,
                    tenant_id=self.default_tenant,
                )
                return {result_key: {"status": "updated", "memory_id": str(res.id)}}

            if action_type in ("forget", "delete") and memory_id:
                hard = bool(action_data.get("hard", False))
                success = await engine.forget(
                    memory_id=memory_id,
                    hard=hard,
                    tenant_id=self.default_tenant,
                )
                return {
                    result_key: {
                        "status": "deleted" if hard else "tombstoned",
                        "success": success,
                    }
                }

            if action_type == "consolidate":
                ns = action_data.get("namespace", self.default_namespace)
                items = await engine.consolidate(
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )
                return {
                    result_key: {
                        "status": "consolidated",
                        "count": len(items),
                        "items": [str(it.id) for it in items],
                    }
                }

            return {
                result_key: {
                    "status": "error",
                    "reason": f"unrecognized_action_{action_type}",
                }
            }

        def _sync_action(state: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(self.engine, SyncMemoryEngine):
                raise RuntimeError("Sync memory action node requires a SyncMemoryEngine instance.")
            # For SyncMemoryEngine, we run synchronously
            action_data = state.get(action_key)
            if not action_data or not isinstance(action_data, dict):
                return {result_key: {"status": "skipped", "reason": "no_action"}}

            action_type = action_data.get("action", "").lower()
            memory_id_str = action_data.get("memory_id")
            memory_id = UUID(memory_id_str) if memory_id_str else None

            if action_type == "remember":
                content = action_data.get("content", "")
                cat = action_data.get("memory_type", MemoryCategory.SEMANTIC)
                conf = float(action_data.get("confidence", 1.0))
                imp = float(action_data.get("importance", 0.8))
                ns = action_data.get("namespace", self.default_namespace)
                res = self.engine.remember(
                    content=content,
                    memory_type=cat,
                    confidence=conf,
                    importance=imp,
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )
                return {result_key: {"status": "remembered", "memory_id": str(res.id)}}

            if action_type == "update" and memory_id:
                new_content = action_data.get("content")
                meta = action_data.get("metadata")
                res = self.engine.update(
                    memory_id=memory_id,
                    new_content=new_content,
                    metadata_updates=meta,
                    tenant_id=self.default_tenant,
                )
                return {result_key: {"status": "updated", "memory_id": str(res.id)}}

            if action_type in ("forget", "delete") and memory_id:
                hard = bool(action_data.get("hard", False))
                success = self.engine.forget(
                    memory_id=memory_id,
                    hard=hard,
                    tenant_id=self.default_tenant,
                )
                return {
                    result_key: {
                        "status": "deleted" if hard else "tombstoned",
                        "success": success,
                    }
                }

            if action_type == "consolidate":
                ns = action_data.get("namespace", self.default_namespace)
                items = self.engine.consolidate(
                    namespace=ns,
                    tenant_id=self.default_tenant,
                )
                return {
                    result_key: {
                        "status": "consolidated",
                        "count": len(items),
                        "items": [str(it.id) for it in items],
                    }
                }

            return {
                result_key: {
                    "status": "error",
                    "reason": f"unrecognized_action_{action_type}",
                }
            }

        if isinstance(self.engine, SyncMemoryEngine):
            return _sync_action
        return _async_action

    # -----------------------------------------------------------------------
    # 4. Shared Project Memory Node
    # -----------------------------------------------------------------------

    def create_shared_project_node(
        self,
        project_id_key: str = "project_id",
        query_key: str = "query",
        project_context_key: str = "project_knowledge",
        budget_tokens: int = 1536,
    ) -> Callable[[dict[str, Any]], Any]:
        """Create a shared project knowledge node accessible across multi-agent graphs."""

        async def _async_project_memory(state: dict[str, Any]) -> dict[str, Any]:
            project_id = state.get(project_id_key, "shared_project")
            query = state.get(query_key, "")
            project_ns = f"project_{project_id}"

            if not query:
                return {project_context_key: ""}

            if isinstance(self.engine, SyncMemoryEngine):
                recon = self.engine.reconstruct(
                    query=query,
                    namespace=project_ns,
                    budget=budget_tokens,
                    tenant_id=self.default_tenant,
                )
            else:
                recon = await self.engine.reconstruct(
                    query=query,
                    namespace=project_ns,
                    budget=budget_tokens,
                    tenant_id=self.default_tenant,
                )

            return {project_context_key: recon.formatted_context}

        def _sync_project_memory(state: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(self.engine, SyncMemoryEngine):
                raise RuntimeError("Sync shared project node requires a SyncMemoryEngine instance.")
            project_id = state.get(project_id_key, "shared_project")
            query = state.get(query_key, "")
            project_ns = f"project_{project_id}"

            if not query:
                return {project_context_key: ""}

            recon = self.engine.reconstruct(
                query=query,
                namespace=project_ns,
                budget=budget_tokens,
                tenant_id=self.default_tenant,
            )
            return {project_context_key: recon.formatted_context}

        if isinstance(self.engine, SyncMemoryEngine):
            return _sync_project_memory
        return _async_project_memory
