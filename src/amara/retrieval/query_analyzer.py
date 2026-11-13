"""Query normalization, intent classification, and entity extraction engine."""

from __future__ import annotations

import datetime
import re
from typing import ClassVar

from amara.intelligence.normalizer import InputNormalizer
from amara.intelligence.providers.rule_based import RuleBasedEntityExtractor
from amara.retrieval.types import NormalizedQuery, QueryIntent


class QueryAnalyzer:
    """Analyzes, normalizes, and decomposes retrieval queries for multi-modal matching."""

    _STOPWORDS: ClassVar[set[str]] = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "about",
        "into",
        "over",
        "after",
        "what",
        "who",
        "when",
        "where",
        "how",
        "why",
        "which",
        "does",
        "do",
        "did",
        "can",
        "could",
        "would",
        "should",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "my",
        "your",
        "his",
        "her",
        "its",
        "our",
        "their",
        "this",
        "that",
        "these",
        "those",
        "please",
        "tell",
        "me",
        "find",
        "show",
    }

    _PROCEDURAL_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:how to|steps? (?:to|for)|procedure|workflow|runbook|commands? to|"
            r"deploy|build)\b",
            re.IGNORECASE,
        ),
    ]

    _TEMPORAL_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:when did|history|historical|previously|previous|former|past|"
            r"timeline|before|originally)\b",
            re.IGNORECASE,
        ),
    ]

    _PREFERENCE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:prefers?|preference|likes?|dislikes?|favorite|theme|mode)\b",
            re.IGNORECASE,
        ),
    ]

    _FACT_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:what is|who is|where is|which|what are|port|database|runtime|version)\b",
            re.IGNORECASE,
        ),
    ]

    _COMMON_ATTRIBUTES: ClassVar[set[str]] = {
        "port",
        "database",
        "theme",
        "role",
        "language",
        "version",
        "runtime",
        "email",
        "url",
        "address",
        "host",
        "mode",
        "framework",
        "status",
    }

    def __init__(self) -> None:
        self.entity_extractor = RuleBasedEntityExtractor()

    async def analyze(
        self,
        query: str,
        reference_time: datetime.datetime | None = None,
        valid_at: datetime.datetime | None = None,
        time_range: tuple[datetime.datetime | None, datetime.datetime | None] | None = None,
        include_historical: bool = False,
    ) -> NormalizedQuery:
        """Decompose raw query string into normalized search tokens, intent, and entities."""
        cleaned = InputNormalizer.clean(query)

        # 1. Intent classification
        intent = self._classify_intent(cleaned)

        # If user asks about historical states, automatically flag include_historical
        auto_historical = include_historical or (intent == QueryIntent.TEMPORAL_HISTORY)

        # 2. Entity extraction
        extracted_entities = await self.entity_extractor.extract_entities(cleaned)
        entity_names = tuple(e.name for e in extracted_entities)

        # 3. Keyword extraction (normalized, non-stopword tokens and n-grams)
        raw_words = re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", cleaned.lower())
        keywords: list[str] = [w for w in raw_words if w not in self._STOPWORDS and len(w) > 1]

        # 4. Attribute identification
        attributes = tuple(w for w in keywords if w in self._COMMON_ATTRIBUTES)

        return NormalizedQuery(
            original_text=query,
            normalized_text=cleaned,
            intent=intent,
            entities=entity_names,
            attributes=attributes,
            keywords=tuple(keywords),
            reference_time=reference_time,
            valid_at=valid_at,
            time_range=time_range,
            include_historical=auto_historical,
        )

    @classmethod
    def _classify_intent(cls, text: str) -> QueryIntent:
        """Determine primary intent based on structural linguistic cues."""
        for pattern in cls._PROCEDURAL_PATTERNS:
            if pattern.search(text):
                return QueryIntent.PROCEDURAL_GUIDANCE

        for pattern in cls._TEMPORAL_PATTERNS:
            if pattern.search(text):
                return QueryIntent.TEMPORAL_HISTORY

        for pattern in cls._PREFERENCE_PATTERNS:
            if pattern.search(text):
                return QueryIntent.PREFERENCE_CHECK

        for pattern in cls._FACT_PATTERNS:
            if pattern.search(text):
                return QueryIntent.FACT_LOOKUP

        return QueryIntent.GENERAL_REASONING
