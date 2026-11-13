"""REST API route handlers for API key issuance, rotation, and revocation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from amara.server.auth import APIKeyRecord, APIKeyStore
from amara.server.dependencies import get_key_store, require_scope
from amara.server.schemas import (
    APIKeyCreatedResponse,
    APIKeyInfoResponse,
    CreateAPIKeyRequest,
)

router = APIRouter(prefix="/api/v1/auth/keys", tags=["API Keys"])


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a new API key for the caller's tenant",
)
async def create_api_key(
    payload: CreateAPIKeyRequest,
    current_key: APIKeyRecord = Depends(require_scope("admin")),
    key_store: APIKeyStore = Depends(get_key_store),
) -> APIKeyCreatedResponse:
    """Generate a new cryptographically secure API key.

    Returns the raw secret key ONCE. The raw secret is never stored or returned again.
    """
    record, raw_key = key_store.create_key(
        tenant_id=current_key.tenant_id,
        name=payload.name,
        workspace_id=payload.workspace_id,
        scopes=payload.scopes,
        expires_in_days=payload.expires_in_days,
    )
    return APIKeyCreatedResponse(
        key_id=record.key_id,
        name=record.name,
        key_prefix=record.key_prefix,
        raw_key=raw_key,
        scopes=list(record.scopes),
        tenant_id=record.tenant_id,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )


@router.get(
    "",
    response_model=list[APIKeyInfoResponse],
    summary="List active and revoked API keys for tenant",
)
async def list_api_keys(
    current_key: APIKeyRecord = Depends(require_scope("admin")),
    key_store: APIKeyStore = Depends(get_key_store),
) -> list[APIKeyInfoResponse]:
    """List metadata for all issued API keys belonging to caller's tenant."""
    records = key_store.list_keys(current_key.tenant_id)
    return [
        APIKeyInfoResponse(
            key_id=r.key_id,
            name=r.name,
            key_prefix=r.key_prefix,
            scopes=list(r.scopes),
            is_active=r.is_active,
            created_at=r.created_at,
            last_used_at=r.last_used_at,
            expires_at=r.expires_at,
        )
        for r in records
    ]


@router.post(
    "/{key_id}/rotate",
    response_model=APIKeyCreatedResponse,
    summary="Rotate an existing API key's secret",
)
async def rotate_api_key(
    key_id: UUID,
    current_key: APIKeyRecord = Depends(require_scope("admin")),
    key_store: APIKeyStore = Depends(get_key_store),
) -> APIKeyCreatedResponse:
    """Immediately invalidate old secret and issue a replacement raw key."""
    try:
        updated_rec, new_raw_key = key_store.rotate_key(key_id)
        # Ensure caller cannot rotate other tenants' keys
        if updated_rec.tenant_id != current_key.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot rotate keys belonging to a different tenant.",
            )
        return APIKeyCreatedResponse(
            key_id=updated_rec.key_id,
            name=updated_rec.name,
            key_prefix=updated_rec.key_prefix,
            raw_key=new_raw_key,
            scopes=list(updated_rec.scopes),
            tenant_id=updated_rec.tenant_id,
            created_at=updated_rec.created_at,
            expires_at=updated_rec.expires_at,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke an API key immediately",
)
async def revoke_api_key(
    key_id: UUID,
    current_key: APIKeyRecord = Depends(require_scope("admin")),
    key_store: APIKeyStore = Depends(get_key_store),
) -> dict[str, str]:
    """Permanently deactivate an API key."""
    # Check tenant ownership first
    record = key_store._keys_by_id.get(key_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_id}' not found.",
        )
    if record.tenant_id != current_key.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke keys belonging to a different tenant.",
        )

    success = key_store.revoke_key(key_id)
    return {
        "status": "revoked" if success else "failed",
        "key_id": str(key_id),
    }

