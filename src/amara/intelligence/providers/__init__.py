"""Provider interfaces and deterministic extraction adapters for AMARA."""

from __future__ import annotations

from amara.intelligence.providers.base import (
    EmbeddingProviderProtocol,
    EntityExtractionProviderProtocol,
    FactExtractionProviderProtocol,
    LLMExtractionProviderProtocol,
)
from amara.intelligence.providers.mock_llm import MockLLMExtractionProvider
from amara.intelligence.providers.rule_based import (
    DeterministicRuleEmbeddingProvider,
    RuleBasedEntityExtractor,
    RuleBasedFactExtractor,
    RuleBasedIntelligenceProvider,
    RuleBasedSkillExtractor,
)

__all__ = [
    "DeterministicRuleEmbeddingProvider",
    "EmbeddingProviderProtocol",
    "EntityExtractionProviderProtocol",
    "FactExtractionProviderProtocol",
    "LLMExtractionProviderProtocol",
    "MockLLMExtractionProvider",
    "RuleBasedEntityExtractor",
    "RuleBasedFactExtractor",
    "RuleBasedIntelligenceProvider",
    "RuleBasedSkillExtractor",
]
