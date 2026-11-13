"""FastAPI application factory, lifespan management, and global error handling for AMARA."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from amara.exceptions import (
    AmaraError,
    MemoryNotFoundError,
    RetentionLockError,
    TenantIsolationError,
)
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.auth import APIKeyStore
from amara.server.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
)
from amara.server.routes import (
    context_router,
    health_router,
    keys_router,
    memories_router,
    usage_router,
)
from amara.version import __version__


def _get_req_id(request: Request) -> str:
    return getattr(request.state, "request_id", f"req_{uuid4().hex[:16]}")


def create_app(
    engine: MemoryEngine | None = None,
    key_store: APIKeyStore | None = None,
    config: MemoryConfig | None = None,
    rate_limit_per_minute: int = 60,
    max_request_bytes: int = 1_048_576,
) -> FastAPI:
    """Create and configure an enterprise-grade AMARA FastAPI REST application."""
    effective_config = config or MemoryConfig.from_env()
    effective_key_store = key_store or APIKeyStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Initialize engine if not already provided and initialized
        active_engine = getattr(app.state, "engine", None)
        if active_engine is None:
            active_engine = MemoryEngine(config=effective_config)
            await active_engine.initialize()
            app.state.engine = active_engine
        elif not active_engine._initialized:
            await active_engine.initialize()

        yield

        # Graceful cleanup
        if app.state.engine is not None:
            await app.state.engine.close()

    app = FastAPI(
        title="AMARA Cognitive Memory API",
        description=(
            "Open-source, model-agnostic cognitive memory framework providing adaptive "
            "lifecycle management, bitemporal hybrid retrieval, and prompt context reconstruction."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Store shared services in application state
    app.state.engine = engine
    app.state.key_store = effective_key_store
    app.state.config = effective_config

    # Register Middlewares (Order: Outer -> Inner)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=max_request_bytes)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Exception Handlers
    # -----------------------------------------------------------------------

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request payload format or parameters.",
                    "request_id": req_id,
                    "details": exc.errors(),
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(MemoryNotFoundError)
    async def memory_not_found_handler(request: Request, exc: MemoryNotFoundError) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "MEMORY_NOT_FOUND",
                    "message": str(exc),
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(TenantIsolationError)
    async def tenant_isolation_handler(request: Request, exc: TenantIsolationError) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "CROSS_TENANT_ACCESS_DENIED",
                    "message": str(exc),
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RetentionLockError)
    async def retention_lock_handler(request: Request, exc: RetentionLockError) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={
                "error": {
                    "code": "RETENTION_LOCKED",
                    "message": str(exc),
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(AmaraError)
    async def amara_error_handler(request: Request, exc: AmaraError) -> JSONResponse:
        req_id = _get_req_id(request)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "AMARA_ERROR",
                    "message": str(exc),
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    # -----------------------------------------------------------------------
    # Mount Routers
    # -----------------------------------------------------------------------

    app.include_router(health_router)
    app.include_router(memories_router)
    app.include_router(context_router)
    app.include_router(usage_router)
    app.include_router(keys_router)

    return app
