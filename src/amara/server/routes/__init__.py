"""REST API routes for AMARA."""

from __future__ import annotations

from amara.server.routes.context import router as context_router
from amara.server.routes.health import router as health_router
from amara.server.routes.keys import router as keys_router
from amara.server.routes.memories import router as memories_router
from amara.server.routes.usage import router as usage_router

__all__ = [
    "context_router",
    "health_router",
    "keys_router",
    "memories_router",
    "usage_router",
]

