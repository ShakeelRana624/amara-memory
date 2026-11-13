"""Cognitive memory modality classifier for AMARA."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import ClassVar

from amara.enums import MemoryCategory
from amara.intelligence.types import ExtractedFact, ExtractedSkill


class MemoryClassifier:
    """Classifies cognitive input into core memory modalities."""

    # Heuristic pattern signatures
    _WORKING_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:scratchpad|current task|active goal|todo|in-progress|scratch)\b", re.IGNORECASE
        ),
        re.compile(r"^working:\s*", re.IGNORECASE),
    ]

    _PROCEDURAL_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"^(?:\d+[\.)]|[-*])\s*(?:install|run|execute|build|test|deploy|configure|create|git)\b",
            re.MULTILINE | re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:how to|step-by-step|procedure|workflow|run the following|command to)\b",
            re.IGNORECASE,
        ),
    ]

    _SEMANTIC_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:prefers?|likes?|dislikes?|is defined as|is a|are a|known as|rule:|preference)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:always|never|standard for|specification for)\b", re.IGNORECASE),
    ]

    _EPISODIC_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:yesterday|today|last night|earlier|at \d{1,2}:\d{2}|session"
            r"|user said|agent answered|observed)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:ran the test|received response|error occurred|status code)\b", re.IGNORECASE
        ),
    ]

    _ASSOCIATIVE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:associated with|linked to|relates to|connection between|bridging|see also)\b",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def classify(
        cls,
        text: str,
        facts: Sequence[ExtractedFact] = (),
        skills: Sequence[ExtractedSkill] = (),
        explicit_category: MemoryCategory | None = None,
    ) -> MemoryCategory:
        """Classify content into a canonical cognitive memory modality.

        Adaptive memory is handled as a lifecycle management dynamic rather
        than a distinct static content modality.
        """
        if explicit_category is not None:
            return explicit_category

        # 1. Procedural priority: if skills with steps exist
        if skills or any(p.search(text) for p in cls._PROCEDURAL_PATTERNS):
            return MemoryCategory.PROCEDURAL

        # 2. Working memory indicators: explicit scratchpad or ephemeral task markers
        if any(p.search(text) for p in cls._WORKING_PATTERNS):
            return MemoryCategory.WORKING

        # 3. Associative indicators: explicit relational bridging statements
        if any(p.search(text) for p in cls._ASSOCIATIVE_PATTERNS):
            return MemoryCategory.ASSOCIATIVE

        # 4. Semantic indicators: distilled facts or invariant user preferences
        if facts and any(
            f.predicate in {"prefers", "likes", "is_a", "uses", "runs_on"} for f in facts
        ):
            return MemoryCategory.SEMANTIC
        if any(p.search(text) for p in cls._SEMANTIC_PATTERNS):
            return MemoryCategory.SEMANTIC

        # 5. Episodic indicators: narrative events or temporal markers
        if any(p.search(text) for p in cls._EPISODIC_PATTERNS):
            return MemoryCategory.EPISODIC

        # Default fallback: interaction episodes
        return MemoryCategory.EPISODIC
