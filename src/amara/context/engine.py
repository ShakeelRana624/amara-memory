"""Context reconstruction engine implementing evidence ranking, budgeting, and citations."""

from __future__ import annotations

import datetime
import re
from collections.abc import Sequence

from amara.context.token_counter import HeuristicTokenCounter, TokenCounter
from amara.context.types import (
    ContextBudget,
    ContextCitation,
    ContextReconstructionConfig,
    PackedContextItem,
    ReconstructedContext,
)
from amara.enums import MemoryCategory
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.retrieval.types import MemorySearchResult, RetrievalStrategy


def _tokenize(text: str) -> set[str]:
    """Tokenize string into lowercase alphanumeric tokens."""
    return set(re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower()))


def _jaccard_overlap(s1: set[str], s2: set[str]) -> float:
    """Compute token Jaccard similarity."""
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


def _format_temporal_anchor(res: MemorySearchResult) -> str:
    """Generate human-readable temporal anchor string for a memory result."""
    asserted_str = res.temporal_validity.asserted_at.strftime("%Y-%m-%d %H:%M UTC")
    valid_from_str = res.temporal_validity.valid_from.strftime("%Y-%m-%d")

    if res.temporal_validity.valid_to is not None:
        valid_to_str = res.temporal_validity.valid_to.strftime("%Y-%m-%d")
        span = f"[{valid_from_str} to {valid_to_str}]"
    else:
        span = f"[{valid_from_str} to Present]"

    return f"Asserted: {asserted_str} | Valid: {span}"


class ContextReconstructionEngine:
    """Reconstructs token-bounded, citation-attributed context for LLM prompt assembly.

    Stages:
    1. Query acceptance.
    2. Multi-channel retrieval via MemoryRetrievalEngine.
    3. Multi-factor evidence ranking (relevance, confidence, importance).
    4. Abstention gating (insufficient evidence detection).
    5. Redundancy removal via novelty token filtering.
    6. Temporal anchoring.
    7. Pluggable token budget packing.
    8. Structured citation and provenance emission.
    """

    def __init__(
        self,
        retrieval_engine: MemoryRetrievalEngine,
        token_counter: TokenCounter | None = None,
        config: ContextReconstructionConfig | None = None,
    ) -> None:
        self.retrieval_engine = retrieval_engine
        self.token_counter = token_counter or HeuristicTokenCounter()
        self.config = config or ContextReconstructionConfig()

    async def reconstruct(
        self,
        query: str,
        tenant_id: str,
        namespace: str = "default",
        budget: ContextBudget | None = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        memory_types: Sequence[MemoryCategory] | None = None,
        valid_at: datetime.datetime | None = None,
        reference_time: datetime.datetime | None = None,
        include_historical: bool = False,
        top_k: int = 15,
    ) -> ReconstructedContext:
        """Execute the 8-stage context reconstruction pipeline."""
        now = datetime.datetime.now(datetime.UTC)
        effective_budget = budget or ContextBudget()

        # 1 & 2. Retrieval via hybrid memory retrieval engine
        retrieval_response = await self.retrieval_engine.retrieve(
            query=query,
            tenant_id=tenant_id,
            namespace=namespace,
            strategy=strategy,
            top_k=top_k,
            memory_types=memory_types,
            valid_at=valid_at,
            reference_time=reference_time,
            include_historical=include_historical,
        )

        candidates = list(retrieval_response.results)
        total_retrieved = len(candidates)

        # 3. Evidence Ranking: compute composite score
        # Invariant: Keep relevance, epistemic confidence, and intrinsic importance separate,
        # but combine them transparently for evidence ranking.
        scored_candidates: list[tuple[float, MemorySearchResult]] = []
        for cand in candidates:
            composite = (
                self.config.weight_relevance * cand.relevance_score
                + self.config.weight_confidence * cand.confidence
                + self.config.weight_importance * cand.importance
            )
            scored_candidates.append((composite, cand))

        # Sort descending by composite evidence rank score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 4. Abstention Gating: check for insufficient evidence
        abstention_recommended = False
        abstention_reason: str | None = None

        if not scored_candidates:
            abstention_recommended = True
            abstention_reason = "No relevant memory records found matching query."
        else:
            max_relevance = max(c.relevance_score for _, c in scored_candidates)
            if max_relevance < self.config.abstention_threshold:
                abstention_recommended = True
                abstention_reason = (
                    f"Insufficient evidence: highest retrieval relevance ({max_relevance:.2f}) "
                    f"is below confidence threshold ({self.config.abstention_threshold:.2f})."
                )

        # 5. Redundancy Removal & Novelty Filtering
        accepted_candidates: list[tuple[float, MemorySearchResult]] = []
        seen_token_sets: list[set[str]] = []
        omitted_redundant_count = 0

        for comp_score, cand in scored_candidates:
            cand_tokens = _tokenize(cand.normalized_content)
            is_redundant = False

            for seen_set in seen_token_sets:
                sim = _jaccard_overlap(cand_tokens, seen_set)
                if sim >= self.config.redundancy_similarity_threshold:
                    is_redundant = True
                    break

            if is_redundant:
                omitted_redundant_count += 1
                continue

            seen_token_sets.append(cand_tokens)
            accepted_candidates.append((comp_score, cand))

        # 6, 7 & 8. Temporal Anchoring, Pluggable Token Budget Packing, Citations
        header_text = (
            "### AMARA Verified Cognitive Memory Context\n\n"
            if self.config.include_provenance_header
            else ""
        )
        header_tokens = self.token_counter.count_tokens(header_text)

        max_available_for_items = effective_budget.available_memory_tokens - header_tokens
        current_item_tokens = 0

        packed_items: list[PackedContextItem] = []
        citations: list[ContextCitation] = []
        item_text_blocks: list[str] = []
        omitted_budget_count = 0

        citation_idx = 1
        for comp_score, cand in accepted_candidates:
            tag = f"[{self.config.citation_prefix}-{citation_idx}]"
            temporal_anchor = _format_temporal_anchor(cand)

            # Build formatted candidate representation
            cap_type = cand.memory_type.value.capitalize()
            if self.config.include_temporal_anchors:
                item_header = (
                    f"{tag} ({cap_type} | Conf: {cand.confidence:.2f} | {temporal_anchor})"
                )
            else:
                item_header = f"{tag} ({cap_type} | Conf: {cand.confidence:.2f})"

            item_block = f"{item_header}\n{cand.content}\n"
            block_tokens = self.token_counter.count_tokens(item_block)

            # Check if adding this item exceeds budget
            if current_item_tokens + block_tokens > max_available_for_items:
                omitted_budget_count += 1
                continue

            # Item fits into budget
            current_item_tokens += block_tokens
            item_text_blocks.append(item_block)

            packed_item = PackedContextItem(
                citation_index=citation_idx,
                citation_tag=tag,
                memory_id=cand.memory_id,
                content=cand.content,
                token_count=block_tokens,
                composite_rank_score=float(round(comp_score, 4)),
                temporal_anchor=temporal_anchor,
            )
            packed_items.append(packed_item)

            # Build structured citation
            snippet = cand.normalized_content[:120] + (
                "..." if len(cand.normalized_content) > 120 else ""
            )
            citation = ContextCitation(
                citation_index=citation_idx,
                citation_tag=tag,
                memory_id=cand.memory_id,
                source_id=cand.source_id,
                author_id=cand.author_id,
                memory_type=cand.memory_type,
                confidence=cand.confidence,
                importance=cand.importance,
                asserted_at=cand.temporal_validity.asserted_at,
                valid_from=cand.temporal_validity.valid_from,
                valid_to=cand.temporal_validity.valid_to,
                temporal_anchor=temporal_anchor,
                snippet=snippet,
            )
            citations.append(citation)
            citation_idx += 1

        # Check if 0 items packed due to budget constraints
        if not packed_items and total_retrieved > 0 and not abstention_recommended:
            abstention_recommended = True
            abstention_reason = (
                f"Token budget ({effective_budget.max_tokens}) was insufficient to pack "
                f"any retrieved memory evidence."
            )

        # Assemble full formatted context
        if packed_items:
            formatted_context = header_text + "\n".join(item_text_blocks).strip()
        else:
            formatted_context = ""

        total_tokens_used = self.token_counter.count_tokens(formatted_context)
        remaining_budget = max(0, effective_budget.max_tokens - total_tokens_used)

        return ReconstructedContext(
            query=query,
            tenant_id=tenant_id,
            namespace=namespace,
            formatted_context=formatted_context,
            citations=tuple(citations),
            packed_items=tuple(packed_items),
            total_tokens_used=total_tokens_used,
            remaining_token_budget=remaining_budget,
            abstention_recommended=abstention_recommended,
            abstention_reason=abstention_reason,
            candidates_retrieved=total_retrieved,
            candidates_packed=len(packed_items),
            candidates_omitted_budget=omitted_budget_count,
            candidates_omitted_redundant=omitted_redundant_count,
            reconstructed_at=now,
        )
