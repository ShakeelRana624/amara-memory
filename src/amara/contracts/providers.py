"""Provider adapter contracts for embeddings and extraction."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EmbeddingAdapterProtocol(Protocol):
    """Abstract interface for text embedding generation adapters."""

    @property
    def dimension(self) -> int:
        """Return the vector dimensionality (e.g. 1536)."""
        ...

    @property
    def model_id(self) -> str:
        """Return the model identifier string."""
        ...

    async def embed_text(self, text: str) -> Sequence[float]:
        """Generate a dense vector embedding for a single text string."""
        ...

    async def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        """Generate dense vector embeddings for a sequence of text strings."""
        ...


@runtime_checkable
class ExtractionAdapterProtocol(Protocol):
    """Abstract interface for LLM extraction and structured fact parsing."""

    async def extract_facts(self, text: str) -> Sequence[Mapping[str, Any]]:
        """Extract atomic semantic knowledge assertions from unstructured dialogue."""
        ...
