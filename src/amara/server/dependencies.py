"""FastAPI dependency injection providers for authentication, authorization, and engine access."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any, cast

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from amara.sdk.engine import MemoryEngine
from amara.server.auth import APIKeyRecord, APIKeyStore

api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_engine(request: Request) -> MemoryEngine:
    """Retrieve the global initialized MemoryEngine from application state."""
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=500,
            detail="MemoryEngine is not initialized on application state.",
        )
    return cast(MemoryEngine, engine)


def get_key_store(request: Request) -> APIKeyStore:
    """Retrieve the global APIKeyStore from application state."""
    key_store = getattr(request.app.state, "key_store", None)
    if key_store is None:
        raise HTTPException(
            status_code=500,
            detail="APIKeyStore is not initialized on application state.",
        )
    return cast(APIKeyStore, key_store)


async def get_current_api_key(
    request: Request,
    api_key_header: str | None = Security(api_key_header_scheme),
    bearer_creds: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    key_store: APIKeyStore = Depends(get_key_store),
) -> APIKeyRecord:
    """Extract and verify the caller's API key from X-API-Key header or Bearer token."""
    raw_key = api_key_header or (bearer_creds.credentials if bearer_creds else None)
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail=(
                "Missing API key. Provide via 'X-API-Key' header or 'Authorization: Bearer <key>'."
            ),
        )

    record = key_store.verify_key(raw_key.strip())
    if record is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid, expired, or revoked API key.",
        )

    # Attach to request state for middleware/logging
    request.state.api_key = record
    return record


def require_scope(
    required_scope: str,
) -> Callable[[APIKeyRecord], Coroutine[Any, Any, APIKeyRecord]]:
    """Dependency factory ensuring the authenticated key possesses the specified scope."""

    async def _scope_checker(
        api_key: APIKeyRecord = Depends(get_current_api_key),
    ) -> APIKeyRecord:
        if "admin" in api_key.scopes:
            return api_key
        if required_scope not in api_key.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: API key lacks required scope '{required_scope}'.",
            )
        return api_key

    return _scope_checker
