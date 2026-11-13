"""REST API route handler for usage statistics and telemetry."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from amara.sdk.engine import MemoryEngine
from amara.server.auth import APIKeyRecord
from amara.server.dependencies import get_engine, require_scope
from amara.server.schemas import UsageResponse

router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])


@router.get(
    "",
    response_model=UsageResponse,
    summary="Retrieve tenant cognitive memory distribution and metrics",
)
async def get_usage(
    namespace: str | None = Query(default=None, description="Optional namespace filter."),
    api_key: APIKeyRecord = Depends(require_scope("read")),
    engine: MemoryEngine = Depends(get_engine),
) -> UsageResponse:
    """Retrieve category distribution, lifecycle counts, and average confidence scores."""
    stats = await engine.stats(
        tenant_id=api_key.tenant_id,
        namespace=namespace,
    )
    return UsageResponse(
        tenant_id=stats.tenant_id,
        namespace=stats.namespace,
        total_memories=stats.total_memories,
        by_category=stats.by_category,
        by_status=stats.by_status,
        average_confidence=stats.average_confidence,
        average_importance=stats.average_importance,
    )

