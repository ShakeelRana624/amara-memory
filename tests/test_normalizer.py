"""Tests for input normalization, sanitization, and cryptographic hashing."""

from __future__ import annotations

import pytest

from amara.exceptions import MemoryValidationError
from amara.intelligence.normalizer import InputNormalizer


def test_clean_standard_text() -> None:
    """Verify basic whitespace compression and stripping."""
    raw = "   Hello   world!   \n   This  is   AMARA.   \n\n"
    cleaned = InputNormalizer.clean(raw)
    assert cleaned == "Hello world!\nThis is AMARA."


def test_clean_unicode_nfkc_normalization() -> None:
    """Verify Unicode NFKC normalization (e.g. ligatures, accents, full-width characters)."""
    # Ligature 'ﬁ' -> 'fi', Full-width 'ＡＭＡＲＡ' -> 'AMARA'
    raw = "The ﬁle was stored in ＡＭARA."
    cleaned = InputNormalizer.clean(raw)
    assert cleaned == "The file was stored in AMARA."


def test_clean_ansi_escape_stripping() -> None:
    """Verify ANSI escape codes from terminal logs are cleanly stripped."""
    raw = "\x1b[31;1mError: \x1b[0m\x1b[32mConnection established.\x1b[0m"
    cleaned = InputNormalizer.clean(raw)
    assert cleaned == "Error: Connection established."


def test_clean_unprintable_control_characters() -> None:
    """Verify unprintable control characters are removed while preserving newlines and tabs."""
    raw = "Valid line.\x00\x07\x1f\nSecond\tline with tab.\x08"
    cleaned = InputNormalizer.clean(raw)
    assert cleaned == "Valid line.\nSecond\tline with tab."


def test_validate_and_normalize_valid() -> None:
    """Verify validate_and_normalize returns clean text on valid input."""
    raw = "   Important agent observation.   "
    res = InputNormalizer.validate_and_normalize(raw)
    assert res == "Important agent observation."


def test_validate_and_normalize_empty_rejection() -> None:
    """Verify empty or whitespace-only inputs are rejected with MemoryValidationError."""
    with pytest.raises(MemoryValidationError) as exc_info:
        InputNormalizer.validate_and_normalize("   \n\t   ")
    assert "cannot be empty" in str(exc_info.value)


def test_validate_and_normalize_non_string_rejection() -> None:
    """Verify non-string inputs are rejected."""
    with pytest.raises(MemoryValidationError):
        InputNormalizer.clean(12345)  # type: ignore[arg-type]


def test_validate_and_normalize_length_limit() -> None:
    """Verify exceeding max length limit raises MemoryValidationError."""
    with pytest.raises(MemoryValidationError) as exc_info:
        InputNormalizer.validate_and_normalize("A" * 100, max_length=50)
    assert "exceeds maximum allowed length" in str(exc_info.value)


def test_compute_content_hash_deterministic() -> None:
    """Verify SHA-256 content hashing produces identical digests for equivalent normalized text."""
    text1 = "User prefers dark mode."
    text2 = "   User   prefers   dark   mode.   \n"
    hash1 = InputNormalizer.compute_content_hash(text1)
    hash2 = InputNormalizer.compute_content_hash(text2)

    assert len(hash1) == 64
    assert hash1 == hash2

    hash3 = InputNormalizer.compute_content_hash("User prefers light mode.")
    assert hash1 != hash3
