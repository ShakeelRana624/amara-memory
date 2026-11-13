"""REST API route handlers for memory CRUD, search, and consolidation."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from amara.exceptions import (
    MemoryNotFoundError,
    RetentionLockError,
)
from amara.sdk.engine import MemoryEngine
from amara.server.auth import APIKeyRecord
from amara.server.dependencies import get_engine, require_scope
from amara.server.schemas import (
    ConsolidateRequest,
    ConsolidateResponse,
    CreateMemoryRequest,
    MemoryResponse,
    SearchMemoryRequest,
    SearchResponse,
    UpdateMemoryRequest,
)

router = APIRouter(prefix="/api/v1/memories", tags=["Memories"])


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and remember a new cognitive proposition",
)
async def create_memory(
    payload: CreateMemoryRequest,
    api_key: APIKeyRecord = Depends(require_scope("write")),
    engine: MemoryEngine = Depends(get_engine),
) -> MemoryResponse:
    """Ingest, extract, deduplicate, and persist a new cognitive memory record."""
    item = await engine.remember(
        content=payload.content,
        author_id=payload.author_id,
        memory_type=payload.memory_type,
        confidence=payload.confidence,
        importance=payload.importance,
        tenant_id=api_key.tenant_id,
        namespace=payload.namespace,
        session_id=payload.session_id,
        metadata=payload.metadata,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        evidence=payload.evidence,
    )
    return MemoryResponse(data=item)


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Retrieve a memory record by ID",
)
async def get_memory(
    memory_id: UUID,
    api_key: APIKeyRecord = Depends(require_scope("read")),
    engine: MemoryEngine = Depends(get_engine),
) -> MemoryResponse:
    """Retrieve an active or historical memory record within caller's tenant scope."""
    try:
        inspection = await engine.inspect(memory_id=memory_id, tenant_id=api_key.tenant_id)
        return MemoryResponse(data=inspection.record)
    except MemoryNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.patch(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Update memory content or metadata",
)
async def update_memory(
    memory_id: UUID,
    payload: UpdateMemoryRequest,
    api_key: APIKeyRecord = Depends(require_scope("write")),
    engine: MemoryEngine = Depends(get_engine),
) -> MemoryResponse:
    """Perform a controlled update of a memory record's content or metadata."""
    try:
        updated = await engine.update(
            memory_id=memory_id,
            new_content=payload.content,
            metadata_updates=payload.metadata,
            tenant_id=api_key.tenant_id,
        )
        return MemoryResponse(data=updated)
    except MemoryNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete or tombstone a memory record",
)
async def delete_memory(
    memory_id: UUID,
    hard: bool = Query(default=False, description="Physical purge vs soft tombstone."),
    cascade: bool = Query(default=False, description="Cascade deletion along derivation lineages."),
    force: bool = Query(default=False, description="Override retention lock if authorized."),
    api_key: APIKeyRecord = Depends(require_scope("write")),
    engine: MemoryEngine = Depends(get_engine),
) -> dict[str, Any]:
    """Delete or tombstone a memory record, respecting retention locks and tenant isolation."""
    try:
        success = await engine.forget(
            memory_id=memory_id,
            tenant_id=api_key.tenant_id,
            hard=hard,
            cascade=cascade,
            force=force,
        )
        return {
            "status": "deleted" if hard else "tombstoned",
            "memory_id": str(memory_id),
            "success": success,
        }
    except MemoryNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    except RetentionLockError as err:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(err)) from err


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Multi-channel hybrid memory search",
)
async def search_memories(
    payload: SearchMemoryRequest,
    api_key: APIKeyRecord = Depends(require_scope("read")),
    engine: MemoryEngine = Depends(get_engine),
) -> SearchResponse:
    """Execute hybrid vector, lexical, temporal, and relational search."""
    recall_res = await engine.recall(
        query=payload.query,
        tenant_id=api_key.tenant_id,
        namespace=payload.namespace,
        strategy=payload.strategy,
        top_k=payload.top_k,
        memory_types=payload.memory_types,
        valid_at=payload.valid_at,
        include_historical=payload.include_historical,
    )
    return SearchResponse(
        query=recall_res.query,
        tenant_id=recall_res.tenant_id,
        namespace=recall_res.namespace,
        results=list(recall_res.results),
        total_candidates=recall_res.total_candidates,
        latency_ms=recall_res.latency_ms,
    )


@router.post(
    "/consolidate",
    response_model=ConsolidateResponse,
    summary="Trigger episodic-to-semantic consolidation",
)
async def consolidate_memories(
    payload: ConsolidateRequest,
    api_key: APIKeyRecord = Depends(require_scope("write")),
    engine: MemoryEngine = Depends(get_engine),
) -> ConsolidateResponse:
    """Discover related experience clusters and synthesize semantic concepts."""
    consolidated_items = await engine.consolidate(
        tenant_id=api_key.tenant_id,
        namespace=payload.namespace,
    )
    return ConsolidateResponse(
        tenant_id=api_key.tenant_id,
        namespace=payload.namespace,
        consolidated_count=len(consolidated_items),
        new_semantic_memories=consolidated_items,
    )
