"""Tests for QueryAnalyzer normalization, intent classification, and entity extraction."""

from __future__ import annotations

import datetime

import pytest

from amara.retrieval.query_analyzer import QueryAnalyzer
from amara.retrieval.types import QueryIntent


@pytest.fixture
def analyzer() -> QueryAnalyzer:
    return QueryAnalyzer()


async def test_analyzer_intent_procedural(analyzer: QueryAnalyzer) -> None:
    """Verify procedural intent classification for how-to and workflow queries."""
    res1 = await analyzer.analyze("How to deploy the application to Kubernetes?")
    assert res1.intent == QueryIntent.PROCEDURAL_GUIDANCE

    res2 = await analyzer.analyze("Steps for setting up the local database")
    assert res2.intent == QueryIntent.PROCEDURAL_GUIDANCE


async def test_analyzer_intent_temporal(analyzer: QueryAnalyzer) -> None:
    """Verify temporal intent classification and automatic historical flag setting."""
    res = await analyzer.analyze("What was the previous port before migration?")
    assert res.intent == QueryIntent.TEMPORAL_HISTORY
    assert res.include_historical is True


async def test_analyzer_intent_preference(analyzer: QueryAnalyzer) -> None:
    """Verify preference intent classification for user settings and preferences."""
    res = await analyzer.analyze("Does user Alice prefer dark mode or light mode?")
    assert res.intent == QueryIntent.PREFERENCE_CHECK


async def test_analyzer_intent_fact_lookup(analyzer: QueryAnalyzer) -> None:
    """Verify factual lookup intent for declarative queries."""
    res = await analyzer.analyze("What is the port for PostgreSQL?")
    assert res.intent == QueryIntent.FACT_LOOKUP


async def test_analyzer_entity_and_attribute_extraction(analyzer: QueryAnalyzer) -> None:
    """Verify entity extraction and attribute detection in queries."""
    q = "User Alice uses PostgreSQL on port 5432 with url https://amara.ai"
    res = await analyzer.analyze(q)

    # Entities recognized by RuleBasedEntityExtractor
    assert "Alice" in res.entities or "PostgreSQL" in res.entities
    # Attributes recognized by dictionary
    assert "port" in res.attributes
    assert "url" in res.attributes
    # Stopwords removed from keywords
    assert "alice" in res.keywords or "postgresql" in res.keywords
    assert "the" not in res.keywords
    assert "is" not in res.keywords


async def test_analyzer_temporal_parameters_passed(analyzer: QueryAnalyzer) -> None:
    """Verify explicit time parameters and validity anchors are preserved."""
    t_ref = datetime.datetime(2025, 6, 1, 12, 0, tzinfo=datetime.UTC)
    t_range = (t_ref, t_ref + datetime.timedelta(days=7))

    res = await analyzer.analyze(
        "Current system configuration",
        reference_time=t_ref,
        time_range=t_range,
        include_historical=False,
    )
    assert res.reference_time == t_ref
    assert res.time_range == t_range
    assert res.include_historical is False
