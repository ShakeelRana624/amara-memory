"""Unit tests for AMARA memory policy manager, recency decay, and retention locks."""

from __future__ import annotations

import datetime

import pytest

from amara.enums import LifecycleStatus, MemoryCategory
from amara.lifecycle.policies import MemoryPolicyManager
from amara.lifecycle.types import (
    LifecycleAction,
    RetentionPolicy,
)
from amara.models.record import MemoryRecord


@pytest.fixture
def policy_manager() -> MemoryPolicyManager:
    return MemoryPolicyManager(
        policy=RetentionPolicy(
            decay_half_life_days=30.0,
            decay_activation_threshold=0.35,
            archive_activation_threshold=0.15,
            critical_importance_threshold=0.85,
            min_importance_threshold=0.15,
            auto_archive_expired=True,
            respect_retention_locks=True,
        )
    )


def test_recency_score_exponential_decay(policy_manager: MemoryPolicyManager) -> None:
    """Test that recency decays exponentially according to half-life T_1/2 = 30 days."""
    now = datetime.datetime.now(datetime.UTC)

    # 1. Brand new record (0 days elapsed)
    rec_0 = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Brand new memory assertion",
        memory_type=MemoryCategory.EPISODIC,
        author_id="user_1",
        asserted_at=now,
    )
    score_0 = policy_manager.calculate_recency_score(rec_0, reference_time=now)
    assert pytest.approx(score_0, abs=0.01) == 1.0

    # 2. Record accessed 30 days ago (1 half-life elapsed)
    t_30 = now + datetime.timedelta(days=30)
    score_30 = policy_manager.calculate_recency_score(rec_0, reference_time=t_30)
    assert pytest.approx(score_30, abs=0.02) == 0.50

    # 3. Record accessed 60 days ago (2 half-lives elapsed)
    t_60 = now + datetime.timedelta(days=60)
    score_60 = policy_manager.calculate_recency_score(rec_0, reference_time=t_60)
    assert pytest.approx(score_60, abs=0.02) == 0.25


def test_recency_never_mutates_intrinsic_importance(policy_manager: MemoryPolicyManager) -> None:
    """Invariant test: Recency decay must NEVER decrease intrinsic record.importance."""
    now = datetime.datetime.now(datetime.UTC)
    record = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Critical security policy: All API requests require JWT authentication.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="security_team",
        importance=0.95,
        asserted_at=now,
    )

    assert record.importance == 0.95

    # Evaluate activation 365 days later
    t_future = now + datetime.timedelta(days=365)
    activation = policy_manager.calculate_activation(record, reference_time=t_future)

    # Intrinsic importance remains unchanged!
    assert record.importance == 0.95
    # High intrinsic importance preserves activation above threshold
    assert activation >= 0.85


def test_utility_reinforcement_influences_activation(policy_manager: MemoryPolicyManager) -> None:
    """Test that positive reinforcement increases utility score and boosts activation."""
    record = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Helpful troubleshooting procedure",
        memory_type=MemoryCategory.PROCEDURAL,
        author_id="assistant",
        importance=0.5,
    )

    initial_activation = policy_manager.calculate_activation(record)

    # Reinforce record with high utility
    record.record_access(utility_delta=4.0)
    boosted_activation = policy_manager.calculate_activation(record)

    assert boosted_activation > initial_activation


def test_retention_lock_protects_against_decay_and_archival(
    policy_manager: MemoryPolicyManager,
) -> None:
    """Test that setting retention_lock=True completely protects record from decay and archival."""
    now = datetime.datetime.now(datetime.UTC)
    old_time = now - datetime.timedelta(days=200)

    record = MemoryRecord.create(
        tenant_id="tenant_1",
        content="User core preference: Always respond in bullet points.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="user_1",
        importance=0.1,  # Low importance
        asserted_at=old_time,
    )
    # Enable retention lock
    record.set_retention_lock(True)
    assert record.is_retention_locked is True

    # Evaluate record after 200 days of inactivity
    result = policy_manager.evaluate_record(record, reference_time=now)

    assert result.is_retention_locked is True
    assert result.recommended_action == LifecycleAction.RETAIN
    assert result.target_status == LifecycleStatus.ACTIVE
    assert "Protected by explicit retention lock" in result.rationale


def test_policy_decay_transition_for_inactive_unimportant_record(
    policy_manager: MemoryPolicyManager,
) -> None:
    """Test that an inactive record with low importance and no utility transitions to DECAYING."""
    now = datetime.datetime.now(datetime.UTC)
    old_time = now - datetime.timedelta(days=90)

    record = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Temporary observation: sky was partly cloudy.",
        memory_type=MemoryCategory.EPISODIC,
        author_id="sensor",
        importance=0.1,
        asserted_at=old_time,
    )

    result = policy_manager.evaluate_record(record, reference_time=now)

    assert result.recommended_action == LifecycleAction.DECAY
    assert result.target_status == LifecycleStatus.DECAYING


def test_temporal_validity_expiration_triggers_archival(
    policy_manager: MemoryPolicyManager,
) -> None:
    """Test that record with valid_to < now triggers expiration/archival recommendation."""
    now = datetime.datetime.now(datetime.UTC)
    yesterday = now - datetime.timedelta(days=1)
    two_days_ago = now - datetime.timedelta(days=2)

    record = MemoryRecord.create(
        tenant_id="tenant_1",
        content="Flash sale discount code SUMMER2026",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="marketing",
        valid_from=two_days_ago,
        valid_to=yesterday,
    )

    result = policy_manager.evaluate_record(record, reference_time=now)

    assert result.is_temporally_expired is True
    assert result.recommended_action == LifecycleAction.ARCHIVE
    assert result.target_status == LifecycleStatus.ARCHIVED
