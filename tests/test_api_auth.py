"""Tests for AMARA API Key Authentication, Rotation, Revocation, and Scope Enforcement."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from amara.server.auth import APIKeyRecord, APIKeyStore
from amara.server.dependencies import require_scope


def test_api_key_generation_and_verification() -> None:
    """Verify API key creation, prefix indexing, SHA-256 secret hashing, and verification."""
    store = APIKeyStore()
    record, raw_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Production Key",
        workspace_id="ws_main",
        scopes={"read", "write"},
    )

    # 1. Inspect format
    assert raw_key.startswith(f"amara_live_{record.key_prefix}_")
    assert record.hashed_secret != raw_key
    assert len(record.hashed_secret) == 64  # SHA-256 hex string

    # 2. Verify with correct raw key
    verified = store.verify_key(raw_key)
    assert verified is not None
    assert verified.key_id == record.key_id
    assert verified.tenant_id == "tenant_alpha"
    assert set(verified.scopes) == {"read", "write"}
    assert verified.last_used_at is not None

    # 3. Verify with invalid or corrupted keys
    assert store.verify_key("invalid_key_string") is None
    assert store.verify_key("amara_live_wrong_secret") is None
    tampered_key = raw_key[:-4] + "ffff"
    assert store.verify_key(tampered_key) is None


def test_api_key_expiration() -> None:
    """Verify expired API keys are rejected immediately."""
    store = APIKeyStore()
    record, raw_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Expiring Key",
        expires_in_days=-1.0,  # Expired in past
    )
    assert record.is_expired() is True
    assert store.verify_key(raw_key) is None


def test_api_key_revocation() -> None:
    """Verify revoked API keys are permanently invalidated."""
    store = APIKeyStore()
    record, raw_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Revocable Key",
    )
    assert store.verify_key(raw_key) is not None

    # Revoke
    revoked = store.revoke_key(record.key_id)
    assert revoked is True
    assert store.verify_key(raw_key) is None

    # Revoking non-existent key returns False
    assert store.revoke_key(uuid4()) is False


def test_api_key_rotation() -> None:
    """Verify key secret rotation replaces credentials while preserving metadata."""
    store = APIKeyStore()
    record, old_raw_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Key To Rotate",
        scopes={"read", "write"},
    )
    assert store.verify_key(old_raw_key) is not None

    # Rotate
    new_record, new_raw_key = store.rotate_key(record.key_id)
    assert new_raw_key != old_raw_key
    assert new_record.key_id == record.key_id
    assert new_record.tenant_id == "tenant_alpha"
    assert set(new_record.scopes) == {"read", "write"}

    # Old key must be invalidated
    assert store.verify_key(old_raw_key) is None
    # New key must be valid
    verified_new = store.verify_key(new_raw_key)
    assert verified_new is not None
    assert verified_new.key_prefix == new_record.key_prefix


@pytest.mark.asyncio
async def test_scope_enforcement_middleware() -> None:
    """Verify FastAPI route authorization enforcement based on API key scopes."""
    store = APIKeyStore()

    _, admin_key = store.create_key(tenant_id="t1", scopes={"admin"})
    _, write_key = store.create_key(tenant_id="t1", scopes={"write"})
    _, read_key = store.create_key(tenant_id="t1", scopes={"read"})

    app = FastAPI()
    app.state.key_store = store

    @app.get("/read-only")
    async def read_endpoint(key: APIKeyRecord = Depends(require_scope("read"))) -> dict[str, str]:
        return {"status": "read_ok", "tenant": key.tenant_id}

    @app.post("/write-only")
    async def write_endpoint(key: APIKeyRecord = Depends(require_scope("write"))) -> dict[str, str]:
        return {"status": "write_ok", "tenant": key.tenant_id}

    @app.delete("/admin-only")
    async def admin_endpoint(key: APIKeyRecord = Depends(require_scope("admin"))) -> dict[str, str]:
        return {"status": "admin_ok", "tenant": key.tenant_id}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Missing Key -> 401
        res = await client.get("/read-only")
        assert res.status_code == 401

        # 2. Invalid Key -> 401
        res = await client.get("/read-only", headers={"Authorization": "Bearer amara_live_bad_key"})
        assert res.status_code == 401

        # 3. Read key accessing read endpoint -> 200
        res = await client.get("/read-only", headers={"Authorization": f"Bearer {read_key}"})
        assert res.status_code == 200
        assert res.json()["status"] == "read_ok"

        # 4. Read key attempting write endpoint -> 403 Forbidden
        res = await client.post("/write-only", headers={"Authorization": f"Bearer {read_key}"})
        assert res.status_code == 403

        # 5. Write key accessing write endpoint -> 200
        res = await client.post("/write-only", headers={"Authorization": f"Bearer {write_key}"})
        assert res.status_code == 200

        # 6. Write key attempting admin endpoint -> 403 Forbidden
        res = await client.delete("/admin-only", headers={"Authorization": f"Bearer {write_key}"})
        assert res.status_code == 403

        # 7. Admin key bypasses all scopes -> 200 on all
        res_r = await client.get("/read-only", headers={"Authorization": f"Bearer {admin_key}"})
        res_w = await client.post("/write-only", headers={"Authorization": f"Bearer {admin_key}"})
        res_a = await client.delete("/admin-only", headers={"Authorization": f"Bearer {admin_key}"})
        assert res_r.status_code == 200
        assert res_w.status_code == 200
        assert res_a.status_code == 200
