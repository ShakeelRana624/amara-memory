"""Tests for intelligence providers: rule-based embeddings, entity extractors, and fact extractors."""

from __future__ import annotations

import math

import pytest

from amara.exceptions import ProviderError
from amara.intelligence.providers.mock_llm import MockLLMExtractionProvider
from amara.intelligence.providers.rule_based import (
    DeterministicRuleEmbeddingProvider,
    RuleBasedEntityExtractor,
    RuleBasedFactExtractor,
    RuleBasedIntelligenceProvider,
    RuleBasedSkillExtractor,
)
from amara.intelligence.types import ExtractedEntity, ExtractedFact, ExtractedSkill
from amara.storage.vector_math import cosine_similarity

# ===========================================================================
# Deterministic Rule Embedding Provider Tests
# ===========================================================================


async def test_rule_embedding_properties_and_norm() -> None:
    """Verify embedding provider returns unit-normalized 1536-dimensional vectors."""
    provider = DeterministicRuleEmbeddingProvider(dimension=1536)
    assert provider.dimension == 1536
    assert provider.model_id == "amara-rule-embedding-v1"

    vec = await provider.embed_text("User prefers dark mode in the IDE.")
    assert len(vec) == 1536

    # Verify L2 unit norm
    l2_norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(l2_norm, abs=1e-5) == 1.0


async def test_rule_embedding_semantic_relative_similarity() -> None:
    """Verify related sentences have higher cosine similarity than unrelated sentences."""
    provider = DeterministicRuleEmbeddingProvider(dimension=1536)

    vec_base = await provider.embed_text("User prefers dark mode in the IDE.")
    vec_similar = await provider.embed_text("User prefers dark theme in the editor.")
    vec_unrelated = await provider.embed_text("Baking a chocolate cake with flour and sugar.")

    sim_similar = cosine_similarity(vec_base, vec_similar)
    sim_unrelated = cosine_similarity(vec_base, vec_unrelated)

    # Similar concepts should have distinctly higher similarity
    assert sim_similar > sim_unrelated
    assert sim_similar > 0.40


async def test_rule_embedding_batch() -> None:
    """Verify embed_batch produces identical vectors to single embed_text calls."""
    provider = DeterministicRuleEmbeddingProvider(dimension=1536)
    texts = [
        "Python 3.12 is the primary runtime.",
        "PostgreSQL with pgvector for persistence.",
    ]

    batch_vecs = await provider.embed_batch(texts)
    single_0 = await provider.embed_text(texts[0])
    single_1 = await provider.embed_text(texts[1])

    assert len(batch_vecs) == 2
    assert batch_vecs[0] == single_0
    assert batch_vecs[1] == single_1


async def test_rule_embedding_empty_text() -> None:
    """Verify empty text returns zero vector."""
    provider = DeterministicRuleEmbeddingProvider(dimension=1536)
    vec = await provider.embed_text("   ")
    assert len(vec) == 1536
    assert all(x == 0.0 for x in vec)


# ===========================================================================
# Rule-Based Entity Extractor Tests
# ===========================================================================


async def test_rule_entity_extractor_technologies_and_preferences() -> None:
    """Verify extraction of recognized technologies, user preferences, and tools."""
    extractor = RuleBasedEntityExtractor()
    text = (
        "User Alice prefers dark mode and uses Python, PostgreSQL with pgvector, "
        "and Docker for deployment."
    )
    entities = await extractor.extract_entities(text)
    names = {e.name for e in entities}
    types = {e.name: e.entity_type for e in entities}

    assert "Python" in names
    assert types["Python"] == "TECHNOLOGY"
    assert "Postgresql" in names
    assert types["Postgresql"] == "TECHNOLOGY"
    assert "Pgvector" in names
    assert "Docker" in names
    assert "dark mode" in names
    assert types["dark mode"] == "PREFERENCE"
    assert "Alice" in names
    assert types["Alice"] == "PERSON"


async def test_rule_entity_extractor_networking_and_contact() -> None:
    """Verify extraction of emails, URLs, IP addresses, and ports."""
    extractor = RuleBasedEntityExtractor()
    text = (
        "Server listening on port 8000 at 192.168.1.10. "
        "Contact admin at support@amara.ai or visit https://github.com/amara-ai/amara."
    )
    entities = await extractor.extract_entities(text)
    names = {e.name for e in entities}

    assert "8000" in names
    assert "192.168.1.10" in names
    assert "support@amara.ai" in names
    assert "https://github.com/amara-ai/amara" in names


# ===========================================================================
# Rule-Based Fact Extractor Tests
# ===========================================================================


async def test_rule_fact_extractor_preferences() -> None:
    """Verify extraction of user preference statements."""
    extractor = RuleBasedFactExtractor()

    text1 = "User prefers dark mode."
    facts1 = await extractor.extract_facts(text1)
    assert len(facts1) >= 1
    assert facts1[0].subject == "User"
    assert facts1[0].predicate == "prefers"
    assert facts1[0].object == "dark mode"
    assert facts1[0].is_negated is False

    text2 = "I prefer concise code."
    facts2 = await extractor.extract_facts(text2)
    assert len(facts2) >= 1
    assert facts2[0].subject == "User"
    assert facts2[0].predicate == "prefers"
    assert facts2[0].object == "concise code"


async def test_rule_fact_extractor_negation() -> None:
    """Verify extraction of negated facts."""
    extractor = RuleBasedFactExtractor()

    text = "User dislikes light mode."
    facts = await extractor.extract_facts(text)
    assert len(facts) >= 1
    assert facts[0].subject == "User"
    assert facts[0].predicate == "likes"
    assert facts[0].object == "light mode"
    assert facts[0].is_negated is True


async def test_rule_fact_extractor_declarative_and_system() -> None:
    """Verify extraction of declarative 'runs on', 'is a', and key-value formats."""
    extractor = RuleBasedFactExtractor()

    text = "Backend runs on port 8000.\nPostgreSQL is a relational database."
    facts = await extractor.extract_facts(text)
    assert len(facts) >= 2

    runs_on_fact = next(f for f in facts if f.predicate == "runs_on")
    assert runs_on_fact.subject == "Backend"
    assert runs_on_fact.object == "port 8000"

    is_a_fact = next(f for f in facts if f.predicate == "is_a")
    assert is_a_fact.subject == "PostgreSQL"
    assert is_a_fact.object == "relational database"


# ===========================================================================
# Rule-Based Skill Extractor Tests
# ===========================================================================


async def test_rule_skill_extractor_procedural_steps() -> None:
    """Verify extraction of procedural steps from numbered sequences."""
    extractor = RuleBasedSkillExtractor()
    text = (
        "# Release Procedure\n"
        "1. Run test suite with pytest\n"
        "2. Run linter with ruff check\n"
        "3. Tag release version\n"
    )
    skills = await extractor.extract_skills(text)
    assert len(skills) == 1
    skill = skills[0]
    assert skill.skill_name == "Release Procedure"
    assert len(skill.steps) == 3
    assert skill.steps[0] == "Run test suite with pytest"
    assert skill.steps[1] == "Run linter with ruff check"
    assert skill.steps[2] == "Tag release version"


# ===========================================================================
# Composite Provider & Mock LLM Provider Tests
# ===========================================================================


async def test_rule_based_intelligence_provider_composite() -> None:
    """Verify composite provider extracts facts, entities, and skills in a single pass."""
    provider = RuleBasedIntelligenceProvider()
    text = (
        "# Deployment Routine\n"
        "User prefers dark mode.\n"
        "1. Build Docker image\n"
        "2. Push to registry\n"
    )
    facts, entities, skills = await provider.extract_all(text)

    assert len(facts) >= 1
    assert len(entities) >= 1
    assert len(skills) == 1


async def test_mock_llm_provider_success_and_failure() -> None:
    """Verify MockLLMExtractionProvider returns canned results and handles simulated errors."""
    canned_fact = ExtractedFact(subject="Alice", predicate="role", object="Lead Architect")
    canned_entity = ExtractedEntity(name="Alice", entity_type="PERSON")
    canned_skill = ExtractedSkill(
        skill_name="Review", description="PR review", steps=("1. Read diff",)
    )

    mock_provider = MockLLMExtractionProvider(
        canned_facts=[canned_fact],
        canned_entities=[canned_entity],
        canned_skills=[canned_skill],
    )
    facts, entities, skills = await mock_provider.extract_all("Any text")
    assert facts == (canned_fact,)
    assert entities == (canned_entity,)
    assert skills == (canned_skill,)
    assert mock_provider.call_count == 1

    # Verify error simulation
    failing_provider = MockLLMExtractionProvider(
        should_fail=True, failure_message="API quota exceeded"
    )
    with pytest.raises(ProviderError) as exc_info:
        await failing_provider.extract_all("Test")
    assert "API quota exceeded" in str(exc_info.value)
