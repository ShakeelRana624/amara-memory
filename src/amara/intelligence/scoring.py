"""Confidence and importance (salience) scoring engines for AMARA cognitive memory."""

from __future__ import annotations

import re
from typing import ClassVar

from amara.enums import MemoryCategory, ProvenanceSourceType


class ScoringEngine:
    """Evaluates epistemic certainty (confidence) and intrinsic salience (importance)."""

    _BASE_CONFIDENCE_BY_SOURCE: ClassVar[dict[ProvenanceSourceType, float]] = {
        ProvenanceSourceType.SYSTEM_INSTRUCTION: 1.0,
        ProvenanceSourceType.USER_INPUT: 0.95,
        ProvenanceSourceType.TOOL_EXECUTION: 0.90,
        ProvenanceSourceType.CONSOLIDATION_SYNTHESIS: 0.85,
        ProvenanceSourceType.ENVIRONMENT_PERCEPT: 0.80,
        ProvenanceSourceType.AGENT_REASONING: 0.75,
    }

    _CERTAINTY_BOOST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:definitely|certainly|always|confirmed|verified|guaranteed|must)\b",
        re.IGNORECASE,
    )
    _CERTAINTY_PENALTY_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:maybe|perhaps|might|possibly|guess|think|seems|unconfirmed|not sure)\b",
        re.IGNORECASE,
    )

    _CRITICAL_IMPORTANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:critical|urgent|vital|security|password|credential|secret|api[-_]?key|crucial)\b",
        re.IGNORECASE,
    )
    _HIGH_IMPORTANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(?:important|remember|always|never|preference|policy|requirement|architecture)\b",
        re.IGNORECASE,
    )
    _EPHEMERAL_IMPORTANCE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:hello|hi|hey|thanks|thank you|ok|okay|bye|goodbye|cool|got it)\b",
        re.IGNORECASE,
    )

    _MODALITY_BASE_IMPORTANCE: ClassVar[dict[MemoryCategory, float]] = {
        MemoryCategory.PROCEDURAL: 0.70,
        MemoryCategory.SEMANTIC: 0.65,
        MemoryCategory.WORKING: 0.60,
        MemoryCategory.ASSOCIATIVE: 0.55,
        MemoryCategory.EPISODIC: 0.50,
    }

    @classmethod
    def compute_confidence(
        cls,
        text: str,
        source_type: ProvenanceSourceType = ProvenanceSourceType.USER_INPUT,
        extracted_confidence: float = 1.0,
        is_verified: bool = False,
    ) -> float:
        """Compute calibrated epistemic certainty score in range [0.0, 1.0]."""
        base = cls._BASE_CONFIDENCE_BY_SOURCE.get(source_type, 0.80)

        # Modulate by linguistic certainty markers
        if cls._CERTAINTY_BOOST_PATTERN.search(text):
            base = min(1.0, base + 0.05)
        elif cls._CERTAINTY_PENALTY_PATTERN.search(text):
            base = max(0.1, base - 0.25)

        # Weight by extractor confidence
        score = base * extracted_confidence

        if is_verified:
            score = min(1.0, score + 0.10)

        return round(max(0.0, min(1.0, score)), 4)

    @classmethod
    def compute_importance(
        cls,
        text: str,
        memory_type: MemoryCategory = MemoryCategory.EPISODIC,
        explicit_priority: str | None = None,
    ) -> float:
        """Compute cognitive salience score in range [0.0, 1.0]."""
        if explicit_priority:
            p_upper = explicit_priority.upper()
            if p_upper == "CRITICAL":
                return 1.0
            if p_upper == "HIGH":
                return 0.85
            if p_upper == "MEDIUM":
                return 0.50
            if p_upper == "LOW":
                return 0.25

        # Check explicit linguistic priority markers
        if cls._CRITICAL_IMPORTANCE_PATTERN.search(text):
            return 0.95
        if cls._HIGH_IMPORTANCE_PATTERN.search(text):
            return 0.80
        if cls._EPHEMERAL_IMPORTANCE_PATTERN.search(text.strip()):
            return 0.15

        # Modality default
        return cls._MODALITY_BASE_IMPORTANCE.get(memory_type, 0.50)
