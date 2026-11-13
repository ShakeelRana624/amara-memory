"""Synchronous wrapper for AMARA MemoryEngine backed by an isolated event loop."""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import datetime
import threading
from collections.abc import Sequence
from types import TracebackType
from typing import Any, cast
from uuid import UUID

from amara.context.types import ContextBudget, ReconstructedContext
from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.sdk.types import (
    EngineStats,
    InspectionResult,
    MemoryItem,
    RecallResponse,
)


class SyncMemoryEngine:
    """Thread-safe synchronous adapter for AMARA MemoryEngine.

    Safely isolates asyncio operations inside a dedicated daemon thread to prevent
    event loop collisions in synchronous applications, CLI tools, and Jupyter notebooks.
    """

    def __init__(self, config: MemoryConfig | None = None) -> None:
        self.config = config or MemoryConfig.from_env()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._async_engine: MemoryEngine | None = None
        self._ready_event = threading.Event()
        self._closed = False

        self._start_loop()

    def _start_loop(self) -> None:
        """Spawn background worker thread and initialize isolated event loop."""

        def _runner() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._async_engine = MemoryEngine(config=self.config)
            self._loop.run_until_complete(self._async_engine.initialize())
            self._ready_event.set()
            try:
                self._loop.run_forever()
            finally:
                try:
                    # Cancel any lingering tasks
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        self._loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass
                self._loop.close()

        self._thread = threading.Thread(target=_runner, daemon=True, name="AMARA-SyncWorker")
        self._thread.start()
        self._ready_event.wait(timeout=15.0)

        if not self._ready_event.is_set():
            raise TimeoutError("Failed to initialize AMARA SyncMemoryEngine worker loop.")

    def _run_sync(self, coro: Any) -> Any:
        """Dispatch coroutine to isolated worker loop and wait for result."""
        if self._closed or self._loop is None:
            raise RuntimeError("SyncMemoryEngine is closed.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def __enter__(self) -> SyncMemoryEngine:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Shut down the background loop and release storage connections."""
        if self._closed:
            return
        self._closed = True

        if self._loop is not None and self._loop.is_running():
            if self._async_engine is not None:
                future = asyncio.run_coroutine_threadsafe(self._async_engine.close(), self._loop)
                with contextlib.suppress(concurrent.futures.TimeoutError, Exception):
                    future.result(timeout=5.0)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    # -----------------------------------------------------------------------
    # Synchronous Operations
    # -----------------------------------------------------------------------

    def remember(
        self,
        content: str,
        author_id: str = "user",
        memory_type: MemoryCategory | str | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        tenant_id: str | None = None,
        namespace: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> MemoryItem:
        """Synchronously remember a new proposition."""
        assert self._async_engine is not None
        return cast(
            MemoryItem,
            self._run_sync(
                self._async_engine.remember(
                    content=content,
                    author_id=author_id,
                    memory_type=memory_type,
                    confidence=confidence,
                    importance=importance,
                    tenant_id=tenant_id,
                    namespace=namespace,
                    session_id=session_id,
                    metadata=metadata,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    evidence=evidence,
                )
            ),
        )

    def recall(
        self,
        query: str,
        tenant_id: str | None = None,
        namespace: str | None = None,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
        top_k: int = 10,
        memory_types: Sequence[MemoryCategory] | None = None,
        valid_at: datetime.datetime | None = None,
        reference_time: datetime.datetime | None = None,
        include_historical: bool = False,
    ) -> RecallResponse:
        """Synchronously recall matching memories."""
        assert self._async_engine is not None
        return cast(
            RecallResponse,
            self._run_sync(
                self._async_engine.recall(
                    query=query,
                    tenant_id=tenant_id,
                    namespace=namespace,
                    strategy=strategy,
                    top_k=top_k,
                    memory_types=memory_types,
                    valid_at=valid_at,
                    reference_time=reference_time,
                    include_historical=include_historical,
                )
            ),
        )

    def update(
        self,
        memory_id: UUID | str,
        new_content: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> MemoryItem:
        """Synchronously update memory content or metadata."""
        assert self._async_engine is not None
        return cast(
            MemoryItem,
            self._run_sync(
                self._async_engine.update(
                    memory_id=memory_id,
                    new_content=new_content,
                    metadata_updates=metadata_updates,
                    tenant_id=tenant_id,
                )
            ),
        )

    def forget(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
        hard: bool = False,
        cascade: bool = False,
        force: bool = False,
    ) -> bool:
        """Synchronously forget a memory record."""
        assert self._async_engine is not None
        return cast(
            bool,
            self._run_sync(
                self._async_engine.forget(
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                    hard=hard,
                    cascade=cascade,
                    force=force,
                )
            ),
        )

    def archive(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
        force: bool = False,
    ) -> MemoryItem:
        """Synchronously archive a memory record."""
        assert self._async_engine is not None
        return cast(
            MemoryItem,
            self._run_sync(
                self._async_engine.archive(
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                    force=force,
                )
            ),
        )

    def restore(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
    ) -> MemoryItem:
        """Synchronously restore an archived memory record."""
        assert self._async_engine is not None
        return cast(
            MemoryItem,
            self._run_sync(
                self._async_engine.restore(
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                )
            ),
        )

    def consolidate(
        self,
        tenant_id: str | None = None,
        namespace: str | None = None,
    ) -> list[MemoryItem]:
        """Synchronously trigger consolidation."""
        assert self._async_engine is not None
        return cast(
            list[MemoryItem],
            self._run_sync(
                self._async_engine.consolidate(
                    tenant_id=tenant_id,
                    namespace=namespace,
                )
            ),
        )

    def reconstruct(
        self,
        query: str,
        tenant_id: str | None = None,
        namespace: str | None = None,
        budget: ContextBudget | int | None = None,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
    ) -> ReconstructedContext:
        """Synchronously reconstruct token-bounded context with citations."""
        assert self._async_engine is not None
        return cast(
            ReconstructedContext,
            self._run_sync(
                self._async_engine.reconstruct(
                    query=query,
                    tenant_id=tenant_id,
                    namespace=namespace,
                    budget=budget,
                    strategy=strategy,
                )
            ),
        )

    def inspect(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
    ) -> InspectionResult:
        """Synchronously inspect a memory record."""
        assert self._async_engine is not None
        return cast(
            InspectionResult,
            self._run_sync(
                self._async_engine.inspect(
                    memory_id=memory_id,
                    tenant_id=tenant_id,
                )
            ),
        )

    def stats(
        self,
        tenant_id: str | None = None,
        namespace: str | None = None,
    ) -> EngineStats:
        """Synchronously gather engine distribution statistics."""
        assert self._async_engine is not None
        return cast(
            EngineStats,
            self._run_sync(
                self._async_engine.stats(
                    tenant_id=tenant_id,
                    namespace=namespace,
                )
            ),
        )
