"""Replaceable provider protocol contracts for embeddings, entity extraction, and fact parsing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from amara.intelligence.types import ExtractedEntity, ExtractedFact, ExtractedSkill


@runtime_checkable
class EmbeddingProviderProtocol(Protocol):
    """Abstract interface for dense vector embedding generation."""

    @property
    def dimension(self) -> int:
        """Vector dimensionality (e.g. 1536)."""
        ...

    @property
    def model_id(self) -> str:
        """Model or algorithm identifier."""
        ...

    async def embed_text(self, text: str) -> Sequence[float]:
        """Generate a single dense float vector embedding."""
        ...

    async def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Generate dense float vector embeddings for a sequence of texts."""
        ...


@runtime_checkable
class EntityExtractionProviderProtocol(Protocol):
    """Abstract interface for named entity recognition."""

    async def extract_entities(self, text: str) -> Sequence[ExtractedEntity]:
        """Recognize and extract entities from text."""
        ...


@runtime_checkable
class FactExtractionProviderProtocol(Protocol):
    """Abstract interface for atomic proposition and fact extraction."""

    async def extract_facts(self, text: str) -> Sequence[ExtractedFact]:
        """Extract atomic subject-predicate-object knowledge claims."""
        ...


@runtime_checkable
class LLMExtractionProviderProtocol(Protocol):
    """Abstract interface for composite LLM-based intelligence extraction."""

    async def extract_all(
        self, text: str
    ) -> tuple[Sequence[ExtractedFact], Sequence[ExtractedEntity], Sequence[ExtractedSkill]]:
        """Extract facts, entities, and procedural skills in a single cognitive pass."""
        ...
