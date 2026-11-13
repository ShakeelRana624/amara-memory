"""REST API route handler for context reconstruction and prompt grounding."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from amara.sdk.engine import MemoryEngine
from amara.server.auth import APIKeyRecord
from amara.server.dependencies import get_engine, require_scope
from amara.server.schemas import (
    CitationItem,
    ReconstructContextRequest,
    ReconstructResponse,
)

router = APIRouter(prefix="/api/v1/context", tags=["Context"])


@router.post(
    "/reconstruct",
    response_model=ReconstructResponse,
    summary="Reconstruct token-bounded context with citations",
)
async def reconstruct_context(
    payload: ReconstructContextRequest,
    api_key: APIKeyRecord = Depends(require_scope("read")),
    engine: MemoryEngine = Depends(get_engine),
) -> ReconstructResponse:
    """Reconstruct an 8-stage token-bounded, citation-stamped context prompt block."""
    reconstruction = await engine.reconstruct(
        query=payload.query,
        tenant_id=api_key.tenant_id,
        namespace=payload.namespace,
        budget=payload.budget_tokens,
        strategy=payload.strategy,
    )

    citations = [
        CitationItem(
            citation_tag=c.citation_tag,
            memory_id=c.memory_id,
            source_id=c.source_id,
            author_id=c.author_id,
            confidence=c.confidence,
            importance=c.importance,
            temporal_anchor=c.temporal_anchor,
            snippet=c.snippet,
        )
        for c in reconstruction.citations
    ]

    return ReconstructResponse(
        query=reconstruction.query,
        formatted_context=reconstruction.formatted_context,
        citations=citations,
        total_tokens_used=reconstruction.total_tokens_used,
        remaining_token_budget=reconstruction.remaining_token_budget,
        abstention_recommended=reconstruction.abstention_recommended,
        abstention_reason=reconstruction.abstention_reason,
        candidates_retrieved=reconstruction.candidates_retrieved,
        candidates_packed=reconstruction.candidates_packed,
    )

