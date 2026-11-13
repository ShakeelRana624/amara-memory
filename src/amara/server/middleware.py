"""HTTP middleware for request IDs, payload size limits, and rate limiting."""

from __future__ import annotations

import collections
import time
from collections.abc import Callable
from typing import Any, cast
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generates or propagates unique X-Request-ID across all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
        request.state.request_id = req_id

        response: Response = cast(Response, await call_next(request))
        response.headers["X-Request-ID"] = req_id
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum incoming payload byte limits to protect server resources."""

    def __init__(self, app: Any, max_bytes: int = 1_048_576) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        content_length_str = request.headers.get("Content-Length")
        if content_length_str:
            try:
                length = int(content_length_str)
                if length > self.max_bytes:
                    req_id = getattr(request.state, "request_id", f"req_{uuid4().hex[:16]}")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": (
                                    f"Request payload ({length} bytes) exceeds maximum "
                                    f"allowed size ({self.max_bytes} bytes)."
                                ),
                                "request_id": req_id,
                            }
                        },
                        headers={"X-Request-ID": req_id},
                    )
            except ValueError:
                pass

        return cast(Response, await call_next(request))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per API key or client IP."""

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        exempt_paths: tuple[str, ...] = (
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ),
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.exempt_paths = exempt_paths
        self._history: dict[str, collections.deque[float]] = collections.defaultdict(
            collections.deque
        )

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.url.path in self.exempt_paths:
            return cast(Response, await call_next(request))

        # Derive rate limit key from X-API-Key or client IP
        key = (
            request.headers.get("X-API-Key")
            or request.headers.get("Authorization")
            or (request.client.host if request.client else "unknown")
        )

        now = time.monotonic()
        window_start = now - 60.0

        timestamps = self._history[key]
        # Purge timestamps outside current 60s sliding window
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= self.requests_per_minute:
            retry_after = int(max(1.0, 60.0 - (now - timestamps[0])))
            req_id = getattr(request.state, "request_id", f"req_{uuid4().hex[:16]}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Rate limit of {self.requests_per_minute} requests per minute "
                            f"exceeded. Please retry after backoff."
                        ),
                        "request_id": req_id,
                        "retry_after_seconds": retry_after,
                    }
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": req_id,
                },
            )

        timestamps.append(now)
        return cast(Response, await call_next(request))
