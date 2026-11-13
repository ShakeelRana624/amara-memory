"""Security and tenant isolation penetration tests for AMARA."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from amara.enums import LifecycleStatus, MemoryCategory, RelationType
from amara.exceptions import MemoryNotFoundError, RetentionLockError
from amara.models.relationship import MemoryRelationship
from amara.sdk.config import MemoryConfig
from amara.sdk.engine import MemoryEngine
from amara.server.app import create_app
from amara.server.auth import APIKeyStore


@pytest.fixture
async def sec_engine() -> MemoryEngine:
    config = MemoryConfig(storage_backend="memory")
    engine = MemoryEngine(config=config)
    await engine.initialize()
    return engine


@pytest.fixture
def auth_api_setup(sec_engine: MemoryEngine) -> tuple[Any, APIKeyStore, str, str, UUID]:
    store = APIKeyStore()
    rw_rec, read_write_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Alpha RW Key",
        scopes={"read", "write"},
    )
    _, read_only_key = store.create_key(
        tenant_id="tenant_alpha",
        name="Alpha ReadOnly Key",
        scopes={"read"},
    )
    app = create_app(engine=sec_engine, key_store=store)
    return app, store, read_write_key, read_only_key, rw_rec.key_id


# ===========================================================================
# 1. Strict Tenant Isolation Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_cross_tenant_isolation_storage_layer(sec_engine: MemoryEngine) -> None:
    """Verify Tenant B cannot access, read, search, or mutate Tenant A data."""
    # 1. Tenant A stores sensitive internal credentials
    mem_a = await sec_engine.remember(
        content="Production DB Password for Tenant A: s3cr3t_p@ssw0rd!",
        memory_type=MemoryCategory.SEMANTIC,
        tenant_id="tenant_alpha",
        namespace="credentials",
    )
    assert mem_a.id is not None

    # 2. Tenant B attempts direct lookup by ID -> Must raise MemoryNotFoundError
    with pytest.raises(MemoryNotFoundError):
        await sec_engine.inspect(
            memory_id=mem_a.id,
            tenant_id="tenant_bravo",
        )

    # 3. Tenant B executes search with exact content match
    search_b = await sec_engine.recall(
        query="Production DB Password",
        tenant_id="tenant_bravo",
        namespace="credentials",
    )
    assert len(search_b.results) == 0, "Tenant B search must never leak Tenant A memories"

    # 4. Tenant B attempts to update Tenant A memory -> Must raise MemoryNotFoundError
    with pytest.raises(MemoryNotFoundError):
        await sec_engine.update(
            memory_id=mem_a.id,
            new_content="Hacked Content by Tenant B",
            tenant_id="tenant_bravo",
        )

    # 5. Tenant B attempts to delete Tenant A memory -> Must raise MemoryNotFoundError
    with pytest.raises(MemoryNotFoundError):
        await sec_engine.forget(
            memory_id=mem_a.id,
            hard=True,
            tenant_id="tenant_bravo",
        )

    # Verify original memory in Tenant A remains completely pristine
    mem_a_verify = await sec_engine.inspect(
        memory_id=mem_a.id,
        tenant_id="tenant_alpha",
    )
    assert mem_a_verify is not None
    assert "s3cr3t_p@ssw0rd!" in mem_a_verify.record.content


@pytest.mark.asyncio
async def test_cross_tenant_relationship_traversal_isolation(
    sec_engine: MemoryEngine,
) -> None:
    """Verify associative relationship graph does not leak cross-tenant edges."""
    mem_a1 = await sec_engine.remember(
        content="Server 192.168.1.1 is master node.",
        tenant_id="tenant_alpha",
    )
    mem_a2 = await sec_engine.remember(
        content="Server 192.168.1.2 is replica node.",
        tenant_id="tenant_alpha",
    )
    assert sec_engine._repository is not None
    rel = MemoryRelationship(
        tenant_id="tenant_alpha",
        source_id=mem_a1.id,
        target_id=mem_a2.id,
        relation_type=RelationType.DEPENDS_ON,
    )
    await sec_engine._repository.create_relationship(rel)

    # Tenant Bravo searches for server topology
    results_bravo = await sec_engine.recall(
        query="master and replica server nodes",
        tenant_id="tenant_bravo",
    )
    assert len(results_bravo.results) == 0


# ===========================================================================
# 2. API Key Authentication & Scope Authorization Security
# ===========================================================================


@pytest.mark.asyncio
async def test_api_auth_missing_and_malformed_tokens(
    auth_api_setup: tuple[Any, APIKeyStore, str, str, UUID],
) -> None:
    app, _, _, _, _ = auth_api_setup
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # 1. No Authorization header
        res_no_auth = await client.post("/api/v1/memories", json={"content": "test"})
        assert res_no_auth.status_code == 401
        assert "error" in res_no_auth.json()

        # 2. Malformed Authorization format (not Bearer)
        res_bad_format = await client.post(
            "/api/v1/memories",
            json={"content": "test"},
            headers={"Authorization": "Basic 123456"},
        )
        assert res_bad_format.status_code == 401

        # 3. Invalid API key prefix or signature
        res_bad_key = await client.post(
            "/api/v1/memories",
            json={"content": "test"},
            headers={"Authorization": "Bearer amara_live_fake_token123456"},
        )
        assert res_bad_key.status_code == 401


@pytest.mark.asyncio
async def test_api_auth_scope_enforcement(
    auth_api_setup: tuple[Any, APIKeyStore, str, str, UUID],
) -> None:
    app, _, rw_key, ro_key, _ = auth_api_setup
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Read-only key reading memories -> allowed
        res_ro_get = await client.post(
            "/api/v1/memories/search",
            json={"query": "test query"},
            headers={"Authorization": f"Bearer {ro_key}"},
        )
        assert res_ro_get.status_code == 200

        # Read-only key attempting to write (POST /api/v1/memories) -> 403 Forbidden
        res_ro_write = await client.post(
            "/api/v1/memories",
            json={"content": "Attempted unauthorized write"},
            headers={"Authorization": f"Bearer {ro_key}"},
        )
        assert res_ro_write.status_code == 403

        # Read-write key writing -> allowed
        res_rw_write = await client.post(
            "/api/v1/memories",
            json={"content": "Authorized write with rw key"},
            headers={"Authorization": f"Bearer {rw_key}"},
        )
        assert res_rw_write.status_code == 201


@pytest.mark.asyncio
async def test_api_key_revocation_instant_invalidation(
    auth_api_setup: tuple[Any, APIKeyStore, str, str, UUID],
) -> None:
    app, store, rw_key, _, rw_key_id = auth_api_setup
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Verify key works
        res_valid = await client.post(
            "/api/v1/memories/search",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {rw_key}"},
        )
        assert res_valid.status_code == 200

        # Revoke key directly
        store.revoke_key(rw_key_id)

        # Verify immediate rejection
        res_revoked = await client.post(
            "/api/v1/memories/search",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {rw_key}"},
        )
        assert res_revoked.status_code == 401


# ===========================================================================
# 3. Payload Injection & Sanitization Security
# ===========================================================================


@pytest.mark.asyncio
async def test_sql_injection_resistance_in_search_and_content(
    sec_engine: MemoryEngine,
) -> None:
    """Verify malicious SQL injection strings do not corrupt storage or fail unsafely."""
    sql_payloads = [
        "'; DROP TABLE memory_records CASCADE; --",
        "' OR '1'='1' --",
        "UNION SELECT NULL, username, password FROM users --",
        "1; EXEC xp_cmdshell('dir'); --",
        "Robert'); DROP TABLE Students;--",
    ]

    for payload in sql_payloads:
        # 1. Ingest payload
        item = await sec_engine.remember(
            content=f"User bio with malicious snippet: {payload}",
            metadata={"injection_attempt": payload},
            tenant_id="tenant_sec",
        )
        assert item.id is not None

        # 2. Search using payload
        results = await sec_engine.recall(
            query=payload,
            tenant_id="tenant_sec",
        )
        assert isinstance(results.results, (list, tuple))

        # 3. Context reconstruction using payload
        context = await sec_engine.reconstruct(
            query=payload,
            tenant_id="tenant_sec",
        )
        assert context.total_tokens_used >= 0


@pytest.mark.asyncio
async def test_xss_and_script_payload_safety_in_reconstructed_context(
    sec_engine: MemoryEngine,
) -> None:
    """Verify HTML/Script injection in memory content is preserved safely in raw text."""
    xss_content = "<script>alert('pwned')</script><img src=x onerror=alert(1)>"
    await sec_engine.remember(
        content=xss_content,
        tenant_id="tenant_xss",
    )
    context = await sec_engine.reconstruct(
        query="pwned alert script",
        tenant_id="tenant_xss",
    )
    # The formatted context should contain the text safely as part of prompt reference
    assert xss_content in context.formatted_context
    assert "[REF-1]" in context.formatted_context


# ===========================================================================
# 4. Retention Lock Security
# ===========================================================================


@pytest.mark.asyncio
async def test_retention_lock_security_enforcement(sec_engine: MemoryEngine) -> None:
    """Verify retention-locked records strictly reject deletion and tombstoning."""
    # Ingest critical compliance record
    mem = await sec_engine.remember(
        content="HIPAA Compliance Audit Trail 2026: Protected record.",
        tenant_id="tenant_compliance",
    )

    # Apply retention lock directly on repository record
    assert sec_engine._repository is not None
    rec = await sec_engine._repository.get_by_id("tenant_compliance", mem.id)
    assert rec is not None
    rec.set_retention_lock(True)

    # Attempt to delete -> Must raise RetentionLockError
    with pytest.raises(RetentionLockError):
        await sec_engine.forget(
            memory_id=mem.id,
            hard=False,
            tenant_id="tenant_compliance",
        )

    # Verify memory is still ACTIVE
    rec_after = await sec_engine._repository.get_by_id("tenant_compliance", mem.id)
    assert rec_after is not None
    assert rec_after.status == LifecycleStatus.ACTIVE

    # Unlock retention lock
    rec_after.set_retention_lock(False)

    # Now deletion must succeed
    deleted = await sec_engine.forget(
        memory_id=mem.id,
        hard=False,
        tenant_id="tenant_compliance",
    )
    assert deleted is True

    # Status should now be TOMBSTONED
    rec_tombstoned = await sec_engine._repository.get_by_id("tenant_compliance", mem.id)
    assert rec_tombstoned is not None
    assert rec_tombstoned.status == LifecycleStatus.TOMBSTONED


# ===========================================================================
# 5. Deletion Propagation & Cascade Verification
# ===========================================================================


@pytest.mark.asyncio
async def test_hard_deletion_propagation_cleans_relationships(
    sec_engine: MemoryEngine,
) -> None:
    """Verify hard delete cascades and purges orphaned relationship edges."""
    mem1 = await sec_engine.remember(content="Parent concept A", tenant_id="tenant_cascade")
    mem2 = await sec_engine.remember(content="Child concept B", tenant_id="tenant_cascade")

    assert sec_engine._repository is not None
    rel = MemoryRelationship(
        tenant_id="tenant_cascade",
        source_id=mem1.id,
        target_id=mem2.id,
        relation_type=RelationType.DERIVED_FROM,
    )
    await sec_engine._repository.create_relationship(rel)

    # Hard delete parent concept A with cascade=True
    hard_deleted = await sec_engine.forget(
        memory_id=mem1.id,
        hard=True,
        cascade=True,
        tenant_id="tenant_cascade",
    )
    assert hard_deleted is True

    # Inspect parent -> should be completely gone
    with pytest.raises(MemoryNotFoundError):
        await sec_engine.inspect(mem1.id, tenant_id="tenant_cascade")

    # Child concept B still exists
    child = await sec_engine.inspect(mem2.id, tenant_id="tenant_cascade")
    assert child is not None

    # Relationships of child should have cleaned up the deleted reference
    assert sec_engine._repository is not None
    rels = await sec_engine._repository.get_relationships("tenant_cascade", mem2.id)
    # All relationships pointing to/from mem1 must no longer be active
    assert len(rels) == 0
