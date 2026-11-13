"""Pluggable token counting interfaces and deterministic heuristic implementations."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from amara.exceptions import ConfigurationError


@runtime_checkable
class TokenCounter(Protocol):
    """Protocol for pluggable token counters."""

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text."""
        ...


class HeuristicTokenCounter:
    """Deterministic token counter requiring zero external dependencies.

    Uses word boundary splitting and calibrated character length heuristics
    (averaging ~4 characters per token for English prose and code).
    """

    def __init__(self, chars_per_token: float = 4.0) -> None:
        if chars_per_token <= 0:
            raise ValueError("chars_per_token must be positive.")
        self.chars_per_token = chars_per_token

    def count_tokens(self, text: str) -> int:
        """Estimate token count deterministically."""
        clean = text.strip()
        if not clean:
            return 0

        # Word-based estimate: split by whitespace and common punctuation delimiters
        words = re.findall(r"\b\w+\b|[^\w\s]", clean)
        word_count = len(words)

        # Character-based estimate
        char_count = len(clean)
        char_estimate = math.ceil(char_count / self.chars_per_token)

        # Conservative hybrid estimate: accounts for subword splitting in code/technical terms
        estimate = max(char_estimate, math.ceil(word_count * 1.25))
        return max(1, estimate)


class TiktokenTokenCounter:
    """Adapter for OpenAI tiktoken BPE tokenizer with fallback capability."""

    def __init__(
        self,
        model_or_encoding: str = "cl100k_base",
        allow_fallback: bool = True,
    ) -> None:
        self.encoding_name = model_or_encoding
        self.allow_fallback = allow_fallback
        self._encoder = None
        self._fallback_counter = HeuristicTokenCounter()

        try:
            import tiktoken  # type: ignore[import-not-found]  # noqa: PLC0415
        except ImportError as err:
            if not allow_fallback:
                raise ConfigurationError(
                    "tiktoken package is not installed and allow_fallback=False. "
                    "Install tiktoken or use HeuristicTokenCounter."
                ) from err
        else:
            try:
                self._encoder = tiktoken.get_encoding(model_or_encoding)
            except ValueError:
                self._encoder = tiktoken.encoding_for_model(model_or_encoding)

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken encoder if available, else heuristic fallback."""
        if not text:
            return 0
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        return self._fallback_counter.count_tokens(text)


class CallableTokenCounter:
    """Wraps an arbitrary user-supplied callable function into a TokenCounter."""

    def __init__(self, func: Callable[[str], int]) -> None:
        self._func = func

    def count_tokens(self, text: str) -> int:
        """Execute the wrapped token counting function."""
        return self._func(text)
