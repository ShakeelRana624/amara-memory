"""Tests for memory modality classification and confidence/salience scoring engines."""

from __future__ import annotations

from amara.enums import MemoryCategory, ProvenanceSourceType
from amara.intelligence.classifier import MemoryClassifier
from amara.intelligence.scoring import ScoringEngine
from amara.intelligence.types import ExtractedFact, ExtractedSkill

# ===========================================================================
# Memory Classifier Tests
# ===========================================================================


def test_classify_working_memory() -> None:
    """Verify working memory classification for scratchpad and active goal markers."""
    assert (
        MemoryClassifier.classify("scratchpad: investigate memory leak") == MemoryCategory.WORKING
    )
    assert (
        MemoryClassifier.classify("current task: fix broken migration test")
        == MemoryCategory.WORKING
    )
    assert MemoryClassifier.classify("active goal: achieve 95% coverage") == MemoryCategory.WORKING


def test_classify_procedural_memory() -> None:
    """Verify procedural memory classification for step sequences and workflows."""
    text = "1. Install dependencies with uv\n2. Run pytest suite"
    assert MemoryClassifier.classify(text) == MemoryCategory.PROCEDURAL

    skill = ExtractedSkill(
        skill_name="Deploy", description="Deploy app", steps=("1. Tag", "2. Push")
    )
    assert (
        MemoryClassifier.classify("Deployment routine", skills=[skill]) == MemoryCategory.PROCEDURAL
    )


def test_classify_semantic_memory() -> None:
    """Verify semantic memory classification for preference facts and definitions."""
    fact = ExtractedFact(subject="User", predicate="prefers", object="dark mode")
    assert MemoryClassifier.classify("User settings", facts=[fact]) == MemoryCategory.SEMANTIC
    assert (
        MemoryClassifier.classify("User prefers dark mode in the editor.")
        == MemoryCategory.SEMANTIC
    )
    assert (
        MemoryClassifier.classify("PostgreSQL is a relational database.") == MemoryCategory.SEMANTIC
    )


def test_classify_episodic_memory() -> None:
    """Verify episodic memory classification for temporal narratives and interaction events."""
    assert (
        MemoryClassifier.classify("Yesterday user reported an authentication timeout at 14:30.")
        == MemoryCategory.EPISODIC
    )
    assert (
        MemoryClassifier.classify("Agent ran the test and received error code 500.")
        == MemoryCategory.EPISODIC
    )


def test_classify_associative_memory() -> None:
    """Verify associative memory classification for cross-domain bridging concepts."""
    text = "Vector search is closely associated with dense embedding retrieval."
    assert MemoryClassifier.classify(text) == MemoryCategory.ASSOCIATIVE


def test_classify_explicit_override() -> None:
    """Verify explicit category override takes precedence over heuristics."""
    text = "User prefers dark mode."
    assert (
        MemoryClassifier.classify(text, explicit_category=MemoryCategory.WORKING)
        == MemoryCategory.WORKING
    )


# ===========================================================================
# Scoring Engine Tests
# ===========================================================================


def test_confidence_scoring_source_hierarchy() -> None:
    """Verify source provenance hierarchy: System (1.0) > User (0.95) > Tool (0.90) > Reasoning (0.75)."""
    text = "The server is operational."
    c_sys = ScoringEngine.compute_confidence(
        text, source_type=ProvenanceSourceType.SYSTEM_INSTRUCTION
    )
    c_user = ScoringEngine.compute_confidence(text, source_type=ProvenanceSourceType.USER_INPUT)
    c_tool = ScoringEngine.compute_confidence(text, source_type=ProvenanceSourceType.TOOL_EXECUTION)
    c_agent = ScoringEngine.compute_confidence(
        text, source_type=ProvenanceSourceType.AGENT_REASONING
    )

    assert c_sys >= c_user
    assert c_user >= c_tool
    assert c_tool >= c_agent


def test_confidence_scoring_linguistic_certainty() -> None:
    """Verify certainty boost ('definitely') and hedging penalty ('maybe', 'perhaps')."""
    base = ScoringEngine.compute_confidence(
        "The feature is ready.", source_type=ProvenanceSourceType.USER_INPUT
    )
    boosted = ScoringEngine.compute_confidence(
        "The feature is definitely ready.", source_type=ProvenanceSourceType.USER_INPUT
    )
    hedged = ScoringEngine.compute_confidence(
        "The feature is maybe ready, perhaps.", source_type=ProvenanceSourceType.USER_INPUT
    )

    assert boosted >= base
    assert hedged < base


def test_confidence_scoring_verification_boost() -> None:
    """Verify cryptographic or empirical verification boosts confidence score."""
    unverified = ScoringEngine.compute_confidence("Fact A", is_verified=False)
    verified = ScoringEngine.compute_confidence("Fact A", is_verified=True)
    assert verified > unverified


def test_importance_scoring_priority_levels() -> None:
    """Verify importance reflects critical keywords vs high vs ephemeral greetings."""
    crit = ScoringEngine.compute_importance("CRITICAL: Database password rotated.")
    high = ScoringEngine.compute_importance("IMPORTANT: User preference is dark mode.")
    normal = ScoringEngine.compute_importance("User opened project README.")
    ephemeral = ScoringEngine.compute_importance("Hello! How are you?")

    assert crit >= 0.90
    assert high >= 0.75
    assert normal >= 0.40
    assert ephemeral <= 0.20


def test_importance_explicit_overrides() -> None:
    """Verify explicit priority parameter overrides heuristics."""
    assert ScoringEngine.compute_importance("Any text", explicit_priority="critical") == 1.0
    assert ScoringEngine.compute_importance("Any text", explicit_priority="high") == 0.85
    assert ScoringEngine.compute_importance("Any text", explicit_priority="low") == 0.25
