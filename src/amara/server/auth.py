"""API key management, cryptographic hashing, rotation, and revocation."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets
from collections.abc import Collection
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

KEY_PREFIX_LENGTH = 8
SECRET_BYTES = 24  # produces 32+ urlsafe characters


class APIKeyRecord(BaseModel):
    """Stored representation of an API key without raw secret material."""

    model_config = ConfigDict(frozen=True)

    key_id: UUID
    name: str
    key_prefix: str
    hashed_secret: str
    tenant_id: str
    workspace_id: str | None = None
    scopes: tuple[str, ...] = ("read", "write")
    is_active: bool = True
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    last_used_at: datetime.datetime | None = None
    expires_at: datetime.datetime | None = None

    def is_expired(self, reference_time: datetime.datetime | None = None) -> bool:
        """Check whether the API key has expired."""
        if self.expires_at is None:
            return False
        ref = reference_time or datetime.datetime.now(datetime.UTC)
        return self.expires_at < ref


class APIKeyStore:
    """Thread-safe store for API key metadata and hashed credentials."""

    def __init__(self) -> None:
        self._keys_by_id: dict[UUID, APIKeyRecord] = {}
        self._keys_by_prefix: dict[str, APIKeyRecord] = {}

    def create_key(
        self,
        tenant_id: str,
        name: str = "Default API Key",
        workspace_id: str | None = None,
        scopes: Collection[str] = ("read", "write"),
        expires_in_days: float | None = None,
    ) -> tuple[APIKeyRecord, str]:
        """Generate a cryptographically secure API key and store its hashed credential.

        Returns:
            A tuple of (APIKeyRecord, raw_api_key).
            The raw_api_key is exposed ONLY once at generation time.
        """
        now = datetime.datetime.now(datetime.UTC)
        key_id = uuid4()
        prefix = secrets.token_hex(KEY_PREFIX_LENGTH // 2)
        raw_secret = secrets.token_hex(SECRET_BYTES)
        raw_key = f"amara_live_{prefix}_{raw_secret}"

        hashed_secret = hashlib.sha256(raw_secret.encode()).hexdigest()

        expires_at = None
        if expires_in_days is not None:
            expires_at = now + datetime.timedelta(days=expires_in_days)

        record = APIKeyRecord(
            key_id=key_id,
            name=name,
            key_prefix=prefix,
            hashed_secret=hashed_secret,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            scopes=tuple(sorted(scopes)),
            is_active=True,
            created_at=now,
            last_used_at=None,
            expires_at=expires_at,
        )

        self._keys_by_id[key_id] = record
        self._keys_by_prefix[prefix] = record

        return record, raw_key

    def verify_key(self, raw_key: str) -> APIKeyRecord | None:
        """Validate raw key against stored hashed credential using constant-time comparison."""
        parts = raw_key.split("_", 3)
        # Format: amara_live_{prefix}_{secret}
        if len(parts) != 4 or parts[0] != "amara" or parts[1] != "live":
            return None

        prefix = parts[2]
        secret = parts[3]

        record = self._keys_by_prefix.get(prefix)
        if record is None or not record.is_active or record.is_expired():
            return None

        expected_hash = hashlib.sha256(secret.encode()).hexdigest()
        if not hmac.compare_digest(record.hashed_secret, expected_hash):
            return None

        # Update last_used_at
        now = datetime.datetime.now(datetime.UTC)
        updated = APIKeyRecord(
            key_id=record.key_id,
            name=record.name,
            key_prefix=record.key_prefix,
            hashed_secret=record.hashed_secret,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            scopes=record.scopes,
            is_active=record.is_active,
            created_at=record.created_at,
            last_used_at=now,
            expires_at=record.expires_at,
        )
        self._keys_by_id[record.key_id] = updated
        self._keys_by_prefix[prefix] = updated

        return updated

    def rotate_key(
        self,
        key_id: UUID,
        name: str | None = None,
        expires_in_days: float | None = None,
    ) -> tuple[APIKeyRecord, str]:
        """Rotate key secret, immediately replacing credentials while preserving permissions."""
        record = self._keys_by_id.get(key_id)
        if record is None:
            raise KeyError(f"API key '{key_id}' not found.")

        # Revoke old key prefix lookup
        if record.key_prefix in self._keys_by_prefix:
            del self._keys_by_prefix[record.key_prefix]

        now = datetime.datetime.now(datetime.UTC)
        new_prefix = secrets.token_hex(KEY_PREFIX_LENGTH // 2)
        new_secret = secrets.token_hex(SECRET_BYTES)
        raw_key = f"amara_live_{new_prefix}_{new_secret}"
        hashed_secret = hashlib.sha256(new_secret.encode()).hexdigest()

        expires_at = record.expires_at
        if expires_in_days is not None:
            expires_at = now + datetime.timedelta(days=expires_in_days)

        updated_record = APIKeyRecord(
            key_id=key_id,
            name=name or record.name,
            key_prefix=new_prefix,
            hashed_secret=hashed_secret,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            scopes=record.scopes,
            is_active=True,
            created_at=now,
            last_used_at=None,
            expires_at=expires_at,
        )

        self._keys_by_id[key_id] = updated_record
        self._keys_by_prefix[new_prefix] = updated_record

        return updated_record, raw_key

    def revoke_key(self, key_id: UUID) -> bool:
        """Revoke key immediately, permanently deactivating access."""
        record = self._keys_by_id.get(key_id)
        if record is None:
            return False

        revoked = APIKeyRecord(
            key_id=record.key_id,
            name=record.name,
            key_prefix=record.key_prefix,
            hashed_secret=record.hashed_secret,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            scopes=record.scopes,
            is_active=False,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
        )
        self._keys_by_id[key_id] = revoked
        if record.key_prefix in self._keys_by_prefix:
            del self._keys_by_prefix[record.key_prefix]

        return True

    def list_keys(self, tenant_id: str) -> list[APIKeyRecord]:
        """List all registered key metadata for tenant."""
        return [k for k in self._keys_by_id.values() if k.tenant_id == tenant_id]
