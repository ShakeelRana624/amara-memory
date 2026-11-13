"""AMARA Asynchronous Background Lifecycle Worker.

Executes continuous cognitive maintenance tasks:
1. Temporal Validity Expiration: Expire records whose validity windows have elapsed.
2. Salience Decay: Apply policy-driven utility and salience decay to inactive memories.
3. Cold Archival: Transition degraded memories to cold storage.
4. Cognitive Consolidation: Discover duplicate clusters and synthesize semantic knowledge.
5. Tombstone Purge: Permanently clean up tombstones that exceed retention locks.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any

from amara.lifecycle.manager import MemoryLifecycleManager
from amara.lifecycle.types import ConsolidationPolicy, RetentionPolicy
from amara.sdk.config import MemoryConfig
from amara.storage.database import DatabaseManager
from amara.storage.memory import InMemoryMemoryRepository
from amara.storage.postgres import PostgresMemoryRepository

logger = logging.getLogger("amara.worker")


class CognitiveWorker:
    """Asynchronous maintenance daemon running cognitive lifecycle routines."""

    def __init__(
        self,
        config: MemoryConfig,
        interval_seconds: float = 60.0,
        tenants: list[str] | None = None,
        heartbeat_file: str | None = "/tmp/amara-worker-heartbeat",
    ) -> None:
        self.config = config
        self.interval_seconds = interval_seconds
        self.tenants = tenants or [config.default_tenant_id]
        self.heartbeat_file = heartbeat_file
        self._running = False
        self._stop_event = asyncio.Event()
        self._db_manager: DatabaseManager | None = None
        self._repository: Any = None
        self._lifecycle_manager: MemoryLifecycleManager | None = None
        self._cycle_count = 0

    async def initialize(self) -> None:
        """Initialize database connections and lifecycle manager."""
        logger.info(
            "Initializing AMARA Worker (storage=%s, interval=%.1fs, tenants=%s)",
            self.config.storage_backend,
            self.interval_seconds,
            self.tenants,
        )

        if self.config.storage_backend == "postgres":
            db_url = (
                self.config.database_url
                or os.getenv("AMARA_DATABASE_URL")
                or "postgresql+asyncpg://amara:amara@127.0.0.1:5432/amara_test"
            )
            self._db_manager = DatabaseManager(
                connection_uri=db_url,
                pool_size=self.config.db_pool_size,
                max_overflow=self.config.db_max_overflow,
            )
            await self._db_manager.initialize()
            self._repository = PostgresMemoryRepository(self._db_manager)
        else:
            self._repository = InMemoryMemoryRepository()

        retention_policy = RetentionPolicy(
            decay_half_life_days=self.config.decay_half_life_days,
        )
        consolidation_policy = ConsolidationPolicy(
            similarity_threshold=self.config.similarity_threshold,
        )

        self._lifecycle_manager = MemoryLifecycleManager(
            repository=self._repository,
            retention_policy=retention_policy,
            consolidation_policy=consolidation_policy,
        )
        logger.info("AMARA Worker successfully initialized.")

    async def run_cycle(self) -> dict[str, Any]:
        """Execute a single lifecycle maintenance cycle across all registered tenants."""
        if self._lifecycle_manager is None:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        now = datetime.datetime.now(datetime.UTC)
        self._cycle_count += 1
        cycle_start = asyncio.get_running_loop().time()
        logger.info("Starting maintenance cycle #%d at %s", self._cycle_count, now.isoformat())

        cycle_summary: dict[str, Any] = {
            "cycle": self._cycle_count,
            "started_at": now.isoformat(),
            "tenants": {},
        }

        for tenant_id in self.tenants:
            try:
                res = await self._lifecycle_manager.run_lifecycle_cycle(
                    tenant_id=tenant_id,
                    reference_time=now,
                )
                cycle_summary["tenants"][tenant_id] = res
                logger.info(
                    "Tenant [%s] maintenance complete: %d scanned, %d decayed, "
                    "%d archived, %d consolidated.",
                    tenant_id,
                    res["scanned_records"],
                    res["decayed_records"],
                    res["archived_records"],
                    res["consolidated_clusters"],
                )
            except Exception as exc:
                logger.error(
                    "Error running lifecycle cycle for tenant %s: %s",
                    tenant_id,
                    exc,
                    exc_info=True,
                )
                cycle_summary["tenants"][tenant_id] = {"error": str(exc)}

        duration = asyncio.get_running_loop().time() - cycle_start
        cycle_summary["duration_seconds"] = round(duration, 3)

        if self.heartbeat_file:
            with contextlib.suppress(Exception):
                Path(self.heartbeat_file).write_text(now.isoformat(), encoding="utf-8")

        return cycle_summary

    async def start(self) -> None:
        """Start the continuous maintenance loop until stopped."""
        self._running = True
        logger.info("AMARA Background Worker started. Listening for tasks...")

        while self._running:
            try:
                await self.run_cycle()
            except Exception as exc:
                logger.error("Unexpected worker cycle failure: %s", exc, exc_info=True)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
                break
            except TimeoutError:
                continue

        logger.info("AMARA Worker loop terminated.")
        await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully release database pools and clean up state."""
        self._running = False
        self._stop_event.set()
        logger.info("Shutting down AMARA Worker...")

        if self._db_manager is not None:
            await self._db_manager.close()
            logger.info("Database pool closed.")

        logger.info("AMARA Worker shutdown complete.")

    def stop(self) -> None:
        """Signal the worker to stop after the current cycle completes."""
        self._running = False
        self._stop_event.set()


async def run_worker_main(
    interval: float = 60.0,
    storage: str = "postgres",
    database_url: str | None = None,
    tenants: list[str] | None = None,
) -> None:
    """Entrypoint function for CLI and container launch."""
    logging.basicConfig(
        level=os.getenv("AMARA_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = MemoryConfig(
        storage_backend=storage,
        database_url=database_url or os.getenv("AMARA_DATABASE_URL"),
    )

    tenant_list = tenants or os.getenv("AMARA_WORKER_TENANTS", "default,production").split(",")
    tenant_list = [t.strip() for t in tenant_list if t.strip()]

    worker = CognitiveWorker(
        config=config,
        interval_seconds=interval,
        tenants=tenant_list,
    )

    await worker.initialize()

    loop = asyncio.get_running_loop()

    def handle_signal() -> None:
        logger.info("Received termination signal. Stopping worker gracefully...")
        worker.stop()

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, handle_signal)

    try:
        await worker.start()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Worker interrupted by user/supervisor.")
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(run_worker_main())
