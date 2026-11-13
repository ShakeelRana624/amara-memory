"""FastAPI integration utilities for using AMARA as an external cognitive memory service.

Provides:
- AmaraClient: Asynchronous HTTP client for AMARA REST API service.
- AmaraMemoryDependency: FastAPI route dependency factory with automatic session/tenant scoping.
- AmaraSessionMiddleware: ASGI middleware for injecting memory context into request.state.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import httpx
from fastapi import Header

from amara.enums import MemoryCategory
from amara.retrieval.types import RetrievalStrategy


class AmaraClient:
    """Asynchronous HTTP client for communicating with an external AMARA server."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the AMARA HTTP client.

        Args:
            base_url: Base endpoint URL of AMARA REST API service.
            api_key: Bearer secret token (amara_live_...).
            timeout: HTTP request timeout in seconds.
            client: Optional pre-configured httpx.AsyncClient (e.g., for test transports).
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._external_client = client
        self._internal_client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        if self._internal_client is None or self._internal_client.is_closed:
            self._internal_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        return self._internal_client

    async def close(self) -> None:
        """Close underlying HTTP connections."""
        if self._internal_client is not None and not self._internal_client.is_closed:
            await self._internal_client.aclose()

    async def check_health(self) -> dict[str, Any]:
        """Check system status of AMARA backend."""
        client = await self._get_client()
        res = await client.get("/api/v1/health", headers=self._headers())
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def remember(
        self,
        content: str,
        author_id: str = "fastapi_agent",
        memory_type: MemoryCategory | str = MemoryCategory.EPISODIC,
        confidence: float = 1.0,
        importance: float = 0.5,
        namespace: str = "default",
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest a new cognitive memory proposition."""
        client = await self._get_client()
        payload = {
            "content": content,
            "author_id": author_id,
            "memory_type": str(memory_type),
            "confidence": confidence,
            "importance": importance,
            "namespace": namespace,
            "session_id": session_id,
            "metadata": metadata or {},
        }
        res = await client.post("/api/v1/memories", json=payload, headers=self._headers())
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def search(
        self,
        query: str,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
        top_k: int = 10,
        namespace: str = "default",
        include_historical: bool = False,
    ) -> dict[str, Any]:
        """Execute multi-channel hybrid recall."""
        client = await self._get_client()
        payload = {
            "query": query,
            "strategy": str(strategy),
            "top_k": top_k,
            "namespace": namespace,
            "include_historical": include_historical,
        }
        res = await client.post("/api/v1/memories/search", json=payload, headers=self._headers())
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def reconstruct_context(
        self,
        query: str,
        budget_tokens: int = 2048,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
        namespace: str = "default",
    ) -> dict[str, Any]:
        """Reconstruct token-bounded context prompt with citations."""
        client = await self._get_client()
        payload = {
            "query": query,
            "budget_tokens": budget_tokens,
            "strategy": str(strategy),
            "namespace": namespace,
        }
        res = await client.post(
            "/api/v1/context/reconstruct", json=payload, headers=self._headers()
        )
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def consolidate(self, namespace: str = "default") -> dict[str, Any]:
        """Trigger episodic-to-semantic consolidation in namespace."""
        client = await self._get_client()
        res = await client.post(
            "/api/v1/memories/consolidate",
            json={"namespace": namespace},
            headers=self._headers(),
        )
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def get_usage(self, namespace: str | None = None) -> dict[str, Any]:
        """Retrieve tenant/namespace cognitive usage statistics."""
        client = await self._get_client()
        params = {"namespace": namespace} if namespace else {}
        res = await client.get("/api/v1/usage", params=params, headers=self._headers())
        res.raise_for_status()
        return cast(dict[str, Any], res.json())

    async def forget(self, memory_id: UUID | str, hard: bool = False) -> dict[str, Any]:
        """Delete or tombstone a memory record."""
        client = await self._get_client()
        res = await client.delete(
            f"/api/v1/memories/{memory_id}",
            params={"hard": hard},
            headers=self._headers(),
        )
        res.raise_for_status()
        return cast(dict[str, Any], res.json())


class AmaraMemoryDependency:
    """FastAPI route dependency that provisions a scoped AmaraClient per request."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        default_namespace: str = "default",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.default_namespace = default_namespace
        self._shared_client = client

    async def __call__(
        self,
        _x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
        _x_namespace: str | None = Header(default=None, alias="X-Namespace"),
        authorization: str | None = Header(default=None),
    ) -> AmaraClient:
        """Resolve client and inject request headers."""
        resolved_key = self.api_key
        if authorization and authorization.startswith("Bearer "):
            resolved_key = authorization[7:].strip()

        return AmaraClient(
            base_url=self.base_url,
            api_key=resolved_key,
            client=self._shared_client,
        )


class AmaraSessionMiddleware:
    """Middleware attaching scoped AMARA client and namespace to request.state."""

    def __init__(
        self,
        app: Any,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        default_namespace: str = "default",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.app = app
        self.base_url = base_url
        self.api_key = api_key
        self.default_namespace = default_namespace
        self.shared_client = client

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            raw_ns = headers.get(b"x-namespace", self.default_namespace.encode())
            ns = raw_ns.decode("utf-8", errors="ignore")
            auth = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")
            key = self.api_key
            if auth.startswith("Bearer "):
                key = auth[7:].strip()

            client = AmaraClient(
                base_url=self.base_url,
                api_key=key,
                client=self.shared_client,
            )
            # Store on ASGI scope state
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["amara_client"] = client
            scope["state"]["amara_namespace"] = ns

        await self.app(scope, receive, send)
