"""Lexical keyword and exact-phrase matching retriever."""

from __future__ import annotations

import re
from collections.abc import Sequence

from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.retrieval.types import NormalizedQuery, ScoredMemoryCandidate


class LexicalRetriever:
    """Retrieves and scores memory records based on lexical tokens, keywords, and phrase matches."""

    def __init__(self, repository: MemoryRepository) -> None:
        self.repository = repository

    async def retrieve(
        self,
        query: NormalizedQuery,
        query_filter: QueryFilter,
        top_k: int = 10,
    ) -> Sequence[ScoredMemoryCandidate]:
        """Query repository and compute token-level relevance scores."""
        # 1. Fetch candidate pool matching filter
        spec = QuerySpec(
            filter=query_filter,
            top_k=max(top_k * 5, 50),
            include_tombstoned=False,
        )
        records = await self.repository.query(spec)

        q_clean = query.normalized_text.lower()
        q_keywords = set(query.keywords)
        q_entities = {e.lower() for e in query.entities}
        q_attributes = set(query.attributes)

        scored: list[ScoredMemoryCandidate] = []
        for rec in records:
            content_lower = rec.normalized_content.lower()
            rec_tokens = set(re.findall(r"\b[a-zA-Z0-9_\-\.]+\b", content_lower))

            # 1. Substring / exact phrase match
            exact_phrase_bonus = 0.0
            if q_clean and (q_clean in content_lower):
                exact_phrase_bonus = 0.50

            # 2. Keyword overlap ratio
            matched_keywords = q_keywords.intersection(rec_tokens)
            keyword_score = len(matched_keywords) / len(q_keywords) if q_keywords else 0.0

            # 3. Entity match bonus
            entity_bonus = 0.0
            for ent in q_entities:
                if ent in content_lower:
                    entity_bonus += 0.25
            entity_bonus = min(0.35, entity_bonus)

            # 4. Attribute match bonus
            attr_bonus = 0.0
            for attr in q_attributes:
                if attr in content_lower:
                    attr_bonus += 0.15
            attr_bonus = min(0.20, attr_bonus)

            # Combine lexical score components
            raw_score = (0.50 * keyword_score) + exact_phrase_bonus + entity_bonus + attr_bonus
            final_score = max(0.0, min(1.0, round(raw_score, 4)))

            kw_ratio = f"{len(matched_keywords)}/{len(q_keywords)}"
            explanation = (
                f"Lexical score {final_score:.4f} (keywords: {kw_ratio}, "
                f"exact_phrase: {bool(exact_phrase_bonus)})"
            )

            if final_score > 0.0:
                scored.append(
                    ScoredMemoryCandidate(
                        record=rec,
                        score=final_score,
                        lexical_score=final_score,
                        match_explanation=explanation,
                    )
                )

        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]
