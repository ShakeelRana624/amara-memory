"""REST API route handler for service health checks and diagnostics."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Request

from amara.server.schemas import HealthResponse
from amara.version import __version__

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check and diagnostic probe",
)
async def get_health(request: Request) -> HealthResponse:
    """Return system readiness, engine version, and storage connection status."""
    engine = getattr(request.app.state, "engine", None)
    storage_backend = "unknown"
    db_connected = False

    if engine is not None:
        storage_backend = engine.config.storage_backend
        if engine._db_manager is not None:
            db_connected = await engine._db_manager.check_health()
        elif engine._repository is not None:
            db_connected = True

    return HealthResponse(
        status="healthy",
        version=__version__,
        storage_backend=storage_backend,
        database_connected=db_connected,
        timestamp=datetime.datetime.now(datetime.UTC),
    )
