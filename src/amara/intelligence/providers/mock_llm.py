"""Mock and configurable test LLM provider for simulating extraction scenarios and failures."""

from __future__ import annotations

from collections.abc import Sequence

from amara.exceptions import ProviderError
from amara.intelligence.providers.base import LLMExtractionProviderProtocol
from amara.intelligence.types import ExtractedEntity, ExtractedFact, ExtractedSkill


class MockLLMExtractionProvider(LLMExtractionProviderProtocol):
    """Configurable test provider for validating failure modes, timeouts, and custom outputs."""

    def __init__(
        self,
        canned_facts: Sequence[ExtractedFact] | None = None,
        canned_entities: Sequence[ExtractedEntity] | None = None,
        canned_skills: Sequence[ExtractedSkill] | None = None,
        should_fail: bool = False,
        failure_message: str = "Simulated upstream provider outage",
    ) -> None:
        self.canned_facts = list(canned_facts or [])
        self.canned_entities = list(canned_entities or [])
        self.canned_skills = list(canned_skills or [])
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.call_count: int = 0

    async def extract_all(
        self, _text: str
    ) -> tuple[Sequence[ExtractedFact], Sequence[ExtractedEntity], Sequence[ExtractedSkill]]:
        self.call_count += 1
        if self.should_fail:
            raise ProviderError("mock_llm", self.failure_message)
        return tuple(self.canned_facts), tuple(self.canned_entities), tuple(self.canned_skills)
