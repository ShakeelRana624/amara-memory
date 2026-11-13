"""Input normalization and sanitization engine for AMARA cognitive memory ingestion."""

from __future__ import annotations

import hashlib
import re
import unicodedata

from amara.exceptions import MemoryValidationError

# Pattern matching ANSI terminal escape codes
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Pattern matching unprintable control characters, preserving standard newline and tab
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")


class InputNormalizer:
    """Sanitizes, normalizes, and validates incoming cognitive inputs for deterministic indexing."""

    @classmethod
    def clean(cls, text: str) -> str:
        """Apply comprehensive Unicode NFKC normalization and control character stripping."""
        if not isinstance(text, str):
            raise MemoryValidationError(
                "content", f"Expected string input, got {type(text).__name__}."
            )

        # 1. Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Strip ANSI escape codes
        stripped_ansi = _ANSI_ESCAPE_PATTERN.sub("", normalized)

        # 3. Strip unprintable control characters
        cleaned_chars = _CONTROL_CHAR_PATTERN.sub("", stripped_ansi)

        # 4. Standardize line endings to LF
        standardized_lines = cleaned_chars.replace("\r\n", "\n").replace("\r", "\n")

        # 5. Compress multiple spaces per line and strip leading/trailing whitespace
        processed_lines = [
            re.sub(r"[ ]+", " ", line).strip() for line in standardized_lines.splitlines()
        ]

        # 6. Reconstruct cleaned text preserving non-redundant paragraph breaks
        return "\n".join(processed_lines).strip()

    @classmethod
    def validate_and_normalize(
        cls, text: str, min_length: int = 1, max_length: int = 1_000_000
    ) -> str:
        """Validate input constraints and return clean normalized text."""
        cleaned = cls.clean(text)
        if len(cleaned) < min_length:
            raise MemoryValidationError(
                "content",
                f"Memory content cannot be empty or whitespace-only (min length {min_length}).",
            )
        if len(cleaned) > max_length:
            raise MemoryValidationError(
                "content",
                f"Memory content exceeds maximum allowed length of {max_length} characters.",
            )
        return cleaned

    @classmethod
    def compute_content_hash(cls, text: str) -> str:
        """Compute deterministic SHA-256 hex digest for integrity and deduplication."""
        cleaned = cls.clean(text)
        return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
