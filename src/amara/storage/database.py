"""PostgreSQL async connection and transaction management for AMARA."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from amara.exceptions import StorageConnectionError

logger = logging.getLogger("amara.storage.database")


class DatabaseManager:
    """Manages PostgreSQL asynchronous connection pools, sessions, and tenant context injection."""

    def __init__(
        self,
        connection_uri: str,
        pool_size: int = 10,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 1800,
        echo: bool = False,
    ) -> None:
        self.connection_uri = connection_uri
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Return the active AsyncEngine, raising error if not initialized."""
        if self._engine is None:
            raise StorageConnectionError(
                "DatabaseManager has not been initialized. Call initialize() first."
            )
        return self._engine

    async def initialize(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Initialize connection pool with exponential backoff on failure."""
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            self.connection_uri,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,
            echo=self.echo,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        # Health check with retry
        for attempt in range(1, max_retries + 1):
            try:
                async with self._engine.connect() as conn:
                    await conn.execute(text("SELECT 1;"))
                logger.info("Successfully connected to PostgreSQL database.")
                return
            except (OperationalError, DBAPIError) as exc:
                if attempt == max_retries:
                    await self.close()
                    raise StorageConnectionError(
                        f"Failed to connect to PostgreSQL after {max_retries} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "Database connection attempt %d/%d failed. Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    retry_delay,
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2.0

    async def check_health(self) -> bool:
        """Verify database connectivity and responsiveness."""
        if self._engine is None:
            return False
        try:
            async with self._engine.connect() as conn:
                res = await conn.execute(text("SELECT 1;"))
                return res.scalar() == 1
        except Exception:
            return False

    async def close(self) -> None:
        """Gracefully dispose of connection pool."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection pool disposed.")

    @asynccontextmanager
    async def session(self, tenant_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
        """Provide an AsyncSession context with optional tenant context injection for RLS."""
        if self._session_factory is None:
            raise StorageConnectionError("DatabaseManager has not been initialized.")

        session: AsyncSession = self._session_factory()
        try:
            if tenant_id is not None:
                # Inject tenant scope into current transaction session for Row-Level Security
                clean_tenant = tenant_id.strip()
                if not clean_tenant:
                    raise ValueError("tenant_id cannot be empty or whitespace.")
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true);"),
                    {"tid": clean_tenant},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
