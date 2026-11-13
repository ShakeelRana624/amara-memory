"""AMARA FastAPI REST server, authentication, and middlewares."""

from __future__ import annotations

from amara.server.app import create_app
from amara.server.auth import APIKeyRecord, APIKeyStore
from amara.server.middleware import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
)

__all__ = [
    "APIKeyRecord",
    "APIKeyStore",
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "RequestSizeLimitMiddleware",
    "create_app",
]

