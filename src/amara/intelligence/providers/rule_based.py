"""Deterministic rule-based providers for embeddings, entity recognition, and fact extraction.

Requires no external network connections, paid LLM APIs, or heavy runtime dependencies.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import ClassVar

from amara.intelligence.providers.base import (
    EmbeddingProviderProtocol,
    EntityExtractionProviderProtocol,
    FactExtractionProviderProtocol,
    LLMExtractionProviderProtocol,
)
from amara.intelligence.types import ExtractedEntity, ExtractedFact, ExtractedSkill

# ---------------------------------------------------------------------------
# Deterministic Feature Hashing Embedding Provider
# ---------------------------------------------------------------------------


class DeterministicRuleEmbeddingProvider(EmbeddingProviderProtocol):
    """Generates deterministic, unit-normalized dense embeddings via feature hashing."""

    def __init__(self, dimension: int = 1536, model_id: str = "amara-rule-embedding-v1") -> None:
        self._dim = dimension
        self._model_id = model_id

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_id(self) -> str:
        return self._model_id

    def _hash_feature(self, feature: str) -> tuple[int, float]:
        """Compute index and sign for feature hashing (Weinberger et al. 2009)."""
        digest = hashlib.md5(feature.encode("utf-8")).hexdigest()
        raw_int = int(digest, 16)
        index = raw_int % self._dim
        sign = 1.0 if ((raw_int >> 31) & 1) == 0 else -1.0
        return index, sign

    def _embed(self, text: str) -> list[float]:
        cleaned = text.strip().lower()
        if not cleaned:
            # Zero vector fallback
            return [0.0] * self._dim

        vec = [0.0] * self._dim

        # 1. Word token features (weight 2.0)
        tokens = re.findall(r"\b\w+\b", cleaned)
        for token in tokens:
            idx, sign = self._hash_feature(f"w_{token}")
            vec[idx] += sign * 2.0

        # 2. Character trigram features (weight 1.0)
        for i in range(len(cleaned) - 2):
            trigram = cleaned[i : i + 3]
            idx, sign = self._hash_feature(f"tri_{trigram}")
            vec[idx] += sign * 1.0

        # 3. Bigram word pairs (weight 1.5)
        for i in range(len(tokens) - 1):
            pair = f"{tokens[i]}_{tokens[i + 1]}"
            idx, sign = self._hash_feature(f"bg_{pair}")
            vec[idx] += sign * 1.5

        # 4. L2 Normalization so dot product equals cosine similarity
        norm_sq = sum(x * x for x in vec)
        if norm_sq > 0.0:
            norm = math.sqrt(norm_sq)
            return [x / norm for x in vec]
        return vec

    async def embed_text(self, text: str) -> Sequence[float]:
        """Generate a dense float vector embedding for a single text string."""
        return self._embed(text)

    async def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Generate dense vector embeddings for multiple texts."""
        return [self._embed(t) for t in texts]


# ---------------------------------------------------------------------------
# Rule-Based Entity Extractor
# ---------------------------------------------------------------------------

_TECH_KEYWORDS = {
    "python",
    "postgresql",
    "postgres",
    "pgvector",
    "docker",
    "linux",
    "git",
    "fastapi",
    "ruff",
    "mypy",
    "pytest",
    "alembic",
    "sqlalchemy",
    "redis",
    "kubernetes",
    "rust",
    "typescript",
    "javascript",
    "golang",
    "sqlite",
}

_PREF_KEYWORDS = {
    "dark mode",
    "light mode",
    "concise",
    "verbose",
    "detailed",
    "minimal",
    "json format",
    "markdown",
    "utc",
    "async",
}


class RuleBasedEntityExtractor(EntityExtractionProviderProtocol):
    """Extracts named entities using deterministic structural and regex patterns."""

    async def extract_entities(self, text: str) -> Sequence[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        seen: set[tuple[str, str]] = set()

        def add_entity(
            name: str, etype: str, start: int | None = None, end: int | None = None
        ) -> None:
            clean_name = name.strip()
            key = (clean_name.lower(), etype)
            if key not in seen and clean_name:
                seen.add(key)
                entities.append(
                    ExtractedEntity(
                        name=clean_name,
                        entity_type=etype,
                        start_char=start,
                        end_char=end,
                        confidence=0.95,
                    )
                )

        # 1. Recognized Technologies
        lower_text = text.lower()
        for tech in _TECH_KEYWORDS:
            for match in re.finditer(rf"\b{re.escape(tech)}\b", lower_text):
                add_entity(tech.title(), "TECHNOLOGY", match.start(), match.end())

        # 2. User Preferences
        for pref in _PREF_KEYWORDS:
            for match in re.finditer(rf"\b{re.escape(pref)}\b", lower_text):
                add_entity(pref, "PREFERENCE", match.start(), match.end())

        # 3. Email Addresses
        for match in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
            add_entity(match.group(), "EMAIL", match.start(), match.end())

        # 4. URLs (stripping trailing sentence punctuation)
        for match in re.finditer(r"https?://[^\s<>\"']+", text):
            clean_url = match.group().rstrip(".,;:!?)")
            add_entity(clean_url, "URL", match.start(), match.start() + len(clean_url))

        # 5. IP Addresses
        for match in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
            add_entity(match.group(), "IP_ADDRESS", match.start(), match.end())

        # 6. Ports
        for match in re.finditer(r"\bport\s+(\d{2,5})\b", text, re.IGNORECASE):
            add_entity(match.group(1), "PORT", match.start(), match.end())

        # 7. Person / User mentions ("User Alice", "My name is Bob", "I am Charlie")
        for match in re.finditer(
            r"\b(?:my name is|i am|call me|user|client|agent)\s+([A-Z][a-z]+)\b",
            text,
            re.IGNORECASE,
        ):
            add_entity(match.group(1), "PERSON", match.start(1), match.end(1))

        if re.search(r"\buser\b", text, re.IGNORECASE):
            add_entity("User", "PERSON")

        return entities


# ---------------------------------------------------------------------------
# Rule-Based Fact Extractor
# ---------------------------------------------------------------------------


class RuleBasedFactExtractor(FactExtractionProviderProtocol):
    """Extracts atomic subject-predicate-object propositions from declarative statements."""

    # Declarative extraction patterns: (regex, subject_group, predicate, object_group, is_negated)
    _PATTERNS: ClassVar[list[tuple[re.Pattern[str], int | None, str, int, bool]]] = [
        # "User prefers dark mode" -> (User, prefers, dark mode)
        (
            re.compile(r"\b(user|agent|client)\s+prefers?\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "prefers",
            2,
            False,
        ),
        # "User likes dark mode" -> (User, likes, dark mode)
        (
            re.compile(r"\b(user|agent|client)\s+likes?\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "likes",
            2,
            False,
        ),
        # "User dislikes light mode" / "User does not like light mode"
        (
            re.compile(r"\b(user|agent|client)\s+dislikes?\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "likes",
            2,
            True,
        ),
        (
            re.compile(
                r"\b(user|agent|client)\s+(?:does not like|doesn't like)\s+([^.,;\n]+)",
                re.IGNORECASE,
            ),
            1,
            "likes",
            2,
            True,
        ),
        # "I prefer dark mode" -> (User, prefers, dark mode)
        (
            re.compile(r"\bi\s+prefer\s+([^.,;\n]+)", re.IGNORECASE),
            None,
            "prefers",
            1,
            False,
        ),
        # "I like Python" -> (User, likes, Python)
        (
            re.compile(r"\bi\s+like\s+([^.,;\n]+)", re.IGNORECASE),
            None,
            "likes",
            1,
            False,
        ),
        # "Server runs on port 8000"
        (
            re.compile(r"\b([a-zA-Z0-9_-]+)\s+runs\s+on\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "runs_on",
            2,
            False,
        ),
        # "Project uses Python 3.12"
        (
            re.compile(r"\b([a-zA-Z0-9_-]+)\s+uses\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "uses",
            2,
            False,
        ),
        # "PostgreSQL is a relational database"
        (
            re.compile(r"\b([a-zA-Z0-9_-]+)\s+is\s+(?:a|an)\s+([^.,;\n]+)", re.IGNORECASE),
            1,
            "is_a",
            2,
            False,
        ),
        # "X is not Y"
        (
            re.compile(r"\b([a-zA-Z0-9_-]+)\s+is\s+not\s+(?:a|an)?\s*([^.,;\n]+)", re.IGNORECASE),
            1,
            "is",
            2,
            True,
        ),
    ]

    async def extract_facts(self, text: str) -> Sequence[ExtractedFact]:
        facts: list[ExtractedFact] = []
        seen: set[tuple[str, str, str, bool]] = set()

        for pattern, subj_idx, predicate, obj_idx, is_neg in self._PATTERNS:
            for match in pattern.finditer(text):
                subj = "User" if subj_idx is None else match.group(subj_idx).strip()
                obj = match.group(obj_idx).strip()

                # Clean trailing periods or conjunctions
                obj = re.sub(r"[\s.]+$", "", obj)
                ctx = match.group(0)

                # Separate scope prepositions for preferences (e.g. "dark mode in the IDE")
                if predicate in {"prefers", "likes"}:
                    prep_m = re.search(
                        r"^(.*?)\s+(?:in|for|at|on)\s+(?:the\s+)?([A-Za-z0-9_ -]+)$",
                        obj,
                        re.IGNORECASE,
                    )
                    if prep_m:
                        core_obj = prep_m.group(1).strip()
                        if core_obj:
                            obj = core_obj

                key = (subj.lower(), predicate.lower(), obj.lower(), is_neg)
                if key not in seen and subj and obj:
                    seen.add(key)
                    facts.append(
                        ExtractedFact(
                            subject=subj.title() if subj.lower() in {"user", "agent"} else subj,
                            predicate=predicate,
                            object=obj,
                            confidence=0.95,
                            is_negated=is_neg,
                            context_snippet=ctx,
                        )
                    )

        # Fallback fact if no pattern matched but sentence has clear "X: Y" key-value format
        if not facts:
            for match in re.finditer(r"^([A-Za-z0-9_ -]+):\s*([^\n]+)$", text, re.MULTILINE):
                k = match.group(1).strip()
                v = match.group(2).strip()
                if k and v:
                    facts.append(
                        ExtractedFact(
                            subject="System",
                            predicate=k.lower().replace(" ", "_"),
                            object=v,
                            confidence=0.90,
                            context_snippet=match.group(0),
                        )
                    )

        return facts


# ---------------------------------------------------------------------------
# Rule-Based Skill & Workflow Extractor
# ---------------------------------------------------------------------------


class RuleBasedSkillExtractor:
    """Extracts procedural workflows and step-by-step procedures from procedural text."""

    _STEP_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?:\d+[\.)]|[-*])\s*(.+)$", re.MULTILINE
    )

    async def extract_skills(self, text: str) -> Sequence[ExtractedSkill]:
        steps = [m.group(1).strip() for m in self._STEP_PATTERN.finditer(text)]
        if len(steps) >= 2:
            # First line or title can serve as skill description
            first_line = text.strip().splitlines()[0]
            name = re.sub(r"^#+\s*", "", first_line)[:64].strip() or "Procedural Workflow"
            return [
                ExtractedSkill(
                    skill_name=name,
                    description=f"Extracted procedure: {name}",
                    steps=tuple(steps),
                )
            ]
        return []


# ---------------------------------------------------------------------------
# Composite Rule-Based Intelligence Provider
# ---------------------------------------------------------------------------


class RuleBasedIntelligenceProvider(LLMExtractionProviderProtocol):
    """Composite provider packaging rule-based entity, fact, and skill extraction."""

    def __init__(self) -> None:
        self.entity_extractor = RuleBasedEntityExtractor()
        self.fact_extractor = RuleBasedFactExtractor()
        self.skill_extractor = RuleBasedSkillExtractor()

    async def extract_all(
        self, text: str
    ) -> tuple[Sequence[ExtractedFact], Sequence[ExtractedEntity], Sequence[ExtractedSkill]]:
        facts = await self.fact_extractor.extract_facts(text)
        entities = await self.entity_extractor.extract_entities(text)
        skills = await self.skill_extractor.extract_skills(text)
        return facts, entities, skills
