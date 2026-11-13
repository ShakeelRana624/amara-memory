"""AMARA Memory Ingestion, Encoding, and Intelligence Subsystem."""

from __future__ import annotations

from amara.intelligence.candidate_generator import MemoryCandidateGenerator
from amara.intelligence.classifier import MemoryClassifier
from amara.intelligence.contradiction import (
    ContradictionCheckResult,
    ContradictionDetector,
)
from amara.intelligence.deduplication import DeduplicationEngine
from amara.intelligence.normalizer import InputNormalizer
from amara.intelligence.pipeline import MemoryIngestionPipeline
from amara.intelligence.provenance import ProvenanceLinker
from amara.intelligence.providers import (
    DeterministicRuleEmbeddingProvider,
    EmbeddingProviderProtocol,
    EntityExtractionProviderProtocol,
    FactExtractionProviderProtocol,
    LLMExtractionProviderProtocol,
    MockLLMExtractionProvider,
    RuleBasedEntityExtractor,
    RuleBasedFactExtractor,
    RuleBasedIntelligenceProvider,
    RuleBasedSkillExtractor,
)
from amara.intelligence.router import MemoryRouter
from amara.intelligence.scoring import ScoringEngine
from amara.intelligence.types import (
    ContradictionCandidate,
    DeduplicationResult,
    ExtractedEntity,
    ExtractedFact,
    ExtractedSkill,
    IngestionCandidate,
    IngestionResult,
)

__all__ = [
    "ContradictionCandidate",
    "ContradictionCheckResult",
    "ContradictionDetector",
    "DeduplicationEngine",
    "DeduplicationResult",
    "DeterministicRuleEmbeddingProvider",
    "EmbeddingProviderProtocol",
    "EntityExtractionProviderProtocol",
    "ExtractedEntity",
    "ExtractedFact",
    "ExtractedSkill",
    "FactExtractionProviderProtocol",
    "IngestionCandidate",
    "IngestionResult",
    "InputNormalizer",
    "LLMExtractionProviderProtocol",
    "MemoryCandidateGenerator",
    "MemoryClassifier",
    "MemoryIngestionPipeline",
    "MemoryRouter",
    "MockLLMExtractionProvider",
    "ProvenanceLinker",
    "RuleBasedEntityExtractor",
    "RuleBasedFactExtractor",
    "RuleBasedIntelligenceProvider",
    "RuleBasedSkillExtractor",
    "ScoringEngine",
]
