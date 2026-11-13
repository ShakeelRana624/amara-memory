"""Memory policy manager implementing multi-attribute evaluation and activation dynamics."""

from __future__ import annotations

import datetime
import math

from amara.enums import LifecycleStatus
from amara.lifecycle.types import (
    LifecycleAction,
    LifecycleEvaluationResult,
    RetentionPolicy,
)
from amara.models.record import MemoryRecord


class MemoryPolicyManager:
    """Evaluates memory records against multi-attribute policies.

    Enforces strict separation between intrinsic importance, epistemic confidence,
    retrieval relevance, and recency.
    """

    def __init__(self, policy: RetentionPolicy | None = None) -> None:
        self.policy = policy or RetentionPolicy()

    def calculate_recency_score(
        self,
        record: MemoryRecord,
        reference_time: datetime.datetime | None = None,
    ) -> float:
        """Calculate exponential recency score based on time elapsed since last access or assertion.

        Uses half-life T_1/2:
            R = 2 ^ (-delta_t / T_half_life)
        """
        ref = reference_time or datetime.datetime.now(datetime.UTC)
        anchor_time = (
            record.last_accessed_at
            or record.temporal.asserted_at
            or record.updated_at
            or record.created_at
        )

        delta_seconds = max(0.0, (ref - anchor_time).total_seconds())
        delta_days = delta_seconds / 86400.0

        half_life_days = max(0.001, self.policy.decay_half_life_days)
        score = math.pow(2.0, -delta_days / half_life_days)
        return float(min(1.0, max(0.0, score)))

    def calculate_utility_score(self, record: MemoryRecord) -> float:
        """Normalize accumulated reinforcement utility into [0.0, 1.0] using logistic sigmoid.

        Positive utility reinforces activation; negative utility diminishes it.
        """
        # Sigmoid centered at 0 with scale factor 2.0
        val = record.utility_score / 2.0
        # Clamp to avoid overflow in exp
        val_clamped = max(-20.0, min(20.0, val))
        return float(1.0 / (1.0 + math.exp(-val_clamped)))

    def calculate_frequency_score(self, record: MemoryRecord) -> float:
        """Calculate access frequency score using diminishing-returns logarithmic scaling."""
        if record.access_count <= 0:
            return 0.0
        # Scale: 1 access -> ~0.29, 5 accesses -> ~0.74, 10+ accesses -> 1.0
        scale = math.log1p(10.0)
        score = math.log1p(record.access_count) / scale
        return float(min(1.0, max(0.0, score)))

    def calculate_activation(
        self,
        record: MemoryRecord,
        reference_time: datetime.datetime | None = None,
    ) -> float:
        """Compute composite cognitive activation score A in [0.0, 1.0].

        Invariant: Recency decays activation over time, but NEVER decreases the intrinsic
        record.importance attribute.
        """
        recency = self.calculate_recency_score(record, reference_time=reference_time)
        utility = self.calculate_utility_score(record)
        frequency = self.calculate_frequency_score(record)
        importance = record.importance

        total_weight = (
            self.policy.weight_recency
            + self.policy.weight_importance
            + self.policy.weight_utility
            + self.policy.weight_frequency
        )
        if total_weight <= 0:
            return importance

        raw_activation = (
            self.policy.weight_recency * recency
            + self.policy.weight_importance * importance
            + self.policy.weight_utility * utility
            + self.policy.weight_frequency * frequency
        ) / total_weight

        # Critical importance guarantees minimal activation floor
        if importance >= self.policy.critical_importance_threshold:
            raw_activation = max(raw_activation, self.policy.critical_importance_threshold)

        return float(min(1.0, max(0.0, raw_activation)))

    def evaluate_record(
        self,
        record: MemoryRecord,
        reference_time: datetime.datetime | None = None,
    ) -> LifecycleEvaluationResult:
        """Evaluate a memory record against policy rules and return recommended lifecycle action."""
        ref = reference_time or datetime.datetime.now(datetime.UTC)

        recency = self.calculate_recency_score(record, reference_time=ref)
        utility = self.calculate_utility_score(record)
        activation = self.calculate_activation(record, reference_time=ref)

        is_locked = record.is_retention_locked and self.policy.respect_retention_locks
        is_expired = False
        if record.temporal.valid_to is not None and record.temporal.valid_to < ref:
            is_expired = True

        # Check maximum age if configured
        age_exceeded = False
        if self.policy.max_age_days is not None:
            age_anchor = record.temporal.asserted_at or record.created_at
            age_days = (ref - age_anchor).total_seconds() / 86400.0
            if age_days > self.policy.max_age_days:
                age_exceeded = True

        current = record.status

        # 1. Tombstoned records remain tombstoned
        if current == LifecycleStatus.TOMBSTONED:
            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=LifecycleAction.DELETE,
                target_status=LifecycleStatus.TOMBSTONED,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=is_locked,
                is_temporally_expired=is_expired,
                rationale="Record is tombstoned and pending physical purge or cleanup.",
            )

        # 2. Retention locked records are protected from decay, archival, and expiration
        if is_locked:
            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=LifecycleAction.RETAIN,
                target_status=current,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=True,
                is_temporally_expired=is_expired,
                rationale="Protected by explicit retention lock. Transitions suppressed.",
            )

        # 3. Temporal validity expiration
        if is_expired:
            v_to = record.temporal.valid_to.isoformat() if record.temporal.valid_to else ""
            if self.policy.auto_archive_expired:
                action = LifecycleAction.ARCHIVE
                target = LifecycleStatus.ARCHIVED
                rationale = f"Temporal validity expired at {v_to}; auto-archiving."
            else:
                action = LifecycleAction.EXPIRE
                target = LifecycleStatus.EXPIRED
                rationale = f"Temporal validity expired at {v_to}."

            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=action,
                target_status=target,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=False,
                is_temporally_expired=True,
                rationale=rationale,
            )

        # 4. Critical importance protection
        if record.importance >= self.policy.critical_importance_threshold:
            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=LifecycleAction.RETAIN,
                target_status=LifecycleStatus.ACTIVE
                if current == LifecycleStatus.DECAYING
                else current,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=False,
                is_temporally_expired=False,
                rationale=(
                    f"High intrinsic importance ({record.importance:.2f} >= "
                    f"{self.policy.critical_importance_threshold:.2f}) protects against decay."
                ),
            )

        # 5. State transitions based on activation
        if current == LifecycleStatus.ACTIVE:
            if activation < self.policy.decay_activation_threshold:
                return LifecycleEvaluationResult(
                    memory_id=record.id,
                    current_status=current,
                    recommended_action=LifecycleAction.DECAY,
                    target_status=LifecycleStatus.DECAYING,
                    activation_score=activation,
                    recency_score=recency,
                    utility_score=utility,
                    importance_score=record.importance,
                    confidence_score=record.confidence,
                    access_count=record.access_count,
                    is_retention_locked=False,
                    is_temporally_expired=False,
                    rationale=(
                        f"Activation ({activation:.2f}) dropped below active threshold "
                        f"({self.policy.decay_activation_threshold:.2f})."
                    ),
                )
            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=LifecycleAction.RETAIN,
                target_status=LifecycleStatus.ACTIVE,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=False,
                is_temporally_expired=False,
                rationale="Active memory satisfies activation criteria.",
            )

        if current == LifecycleStatus.DECAYING:
            if activation < self.policy.archive_activation_threshold or age_exceeded:
                return LifecycleEvaluationResult(
                    memory_id=record.id,
                    current_status=current,
                    recommended_action=LifecycleAction.ARCHIVE,
                    target_status=LifecycleStatus.ARCHIVED,
                    activation_score=activation,
                    recency_score=recency,
                    utility_score=utility,
                    importance_score=record.importance,
                    confidence_score=record.confidence,
                    access_count=record.access_count,
                    is_retention_locked=False,
                    is_temporally_expired=False,
                    rationale=(
                        f"Decaying memory activation ({activation:.2f}) dropped below "
                        f"archive threshold ({self.policy.archive_activation_threshold:.2f})."
                    ),
                )
            return LifecycleEvaluationResult(
                memory_id=record.id,
                current_status=current,
                recommended_action=LifecycleAction.RETAIN,
                target_status=LifecycleStatus.DECAYING,
                activation_score=activation,
                recency_score=recency,
                utility_score=utility,
                importance_score=record.importance,
                confidence_score=record.confidence,
                access_count=record.access_count,
                is_retention_locked=False,
                is_temporally_expired=False,
                rationale="Memory remains decaying but above cold archive threshold.",
            )

        # For ARCHIVED, SUPERSEDED, EXPIRED, CONSOLIDATED
        return LifecycleEvaluationResult(
            memory_id=record.id,
            current_status=current,
            recommended_action=LifecycleAction.RETAIN,
            target_status=current,
            activation_score=activation,
            recency_score=recency,
            utility_score=utility,
            importance_score=record.importance,
            confidence_score=record.confidence,
            access_count=record.access_count,
            is_retention_locked=False,
            is_temporally_expired=is_expired,
            rationale=f"Record is in non-active state '{current.value}'; retaining as-is.",
        )
