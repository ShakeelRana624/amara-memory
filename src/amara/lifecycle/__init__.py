"""AMARA cognitive memory lifecycle subsystem."""

from __future__ import annotations

from amara.lifecycle.consolidation import MemoryConsolidator
from amara.lifecycle.forgetting import ForgettingManager
from amara.lifecycle.manager import MemoryLifecycleManager
from amara.lifecycle.policies import MemoryPolicyManager
from amara.lifecycle.types import (
    ConsolidationCandidate,
    ConsolidationPolicy,
    ConsolidationResult,
    ExpirationResult,
    LifecycleAction,
    LifecycleAuditRecord,
    LifecycleEvaluationResult,
    RetentionPolicy,
)

__all__ = [
    "ConsolidationCandidate",
    "ConsolidationPolicy",
    "ConsolidationResult",
    "ExpirationResult",
    "ForgettingManager",
    "LifecycleAction",
    "LifecycleAuditRecord",
    "LifecycleEvaluationResult",
    "MemoryConsolidator",
    "MemoryLifecycleManager",
    "MemoryPolicyManager",
    "RetentionPolicy",
]
