"""Unit tests for AMARA context reconstruction, token budgeting, citations, and abstention."""

from __future__ import annotations

import datetime

import pytest

from amara.context.engine import ContextReconstructionEngine
from amara.context.token_counter import (
    CallableTokenCounter,
    HeuristicTokenCounter,
    TiktokenTokenCounter,
)
from amara.context.types import (
    ContextBudget,
    ContextReconstructionConfig,
)
from amara.enums import MemoryCategory
from amara.models.record import MemoryRecord
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.storage.memory import InMemoryMemoryRepository


@pytest.fixture
def repo() -> InMemoryMemoryRepository:
    return InMemoryMemoryRepository()


@pytest.fixture
def retrieval_engine(repo: InMemoryMemoryRepository) -> MemoryRetrievalEngine:
    return MemoryRetrievalEngine(repository=repo)


@pytest.fixture
def reconstruction_engine(
    retrieval_engine: MemoryRetrievalEngine,
) -> ContextReconstructionEngine:
    return ContextReconstructionEngine(
        retrieval_engine=retrieval_engine,
        token_counter=HeuristicTokenCounter(chars_per_token=4.0),
        config=ContextReconstructionConfig(
            abstention_threshold=0.35,
            redundancy_similarity_threshold=0.80,
            include_temporal_anchors=True,
            include_provenance_header=True,
        ),
    )


def test_heuristic_token_counter() -> None:
    """Test deterministic heuristic token counting."""
    counter = HeuristicTokenCounter(chars_per_token=4.0)

    assert counter.count_tokens("") == 0
    # "Hello world" -> 11 chars / 4 = 3 tokens, 2 words * 1.25 = 3 tokens
    count = counter.count_tokens("Hello world")
    assert count >= 2
    assert count <= 4

    # Longer technical prompt
    long_text = (
        "The user has configured PostgreSQL 16 with pgvector for vector similarity retrieval."
    )
    assert counter.count_tokens(long_text) > 10


def test_callable_token_counter() -> None:
    """Test pluggable callable token counter adapter."""
    counter = CallableTokenCounter(func=lambda t: len(t.split()))
    assert counter.count_tokens("five words in this sentence") == 5


def test_tiktoken_token_counter_graceful_fallback() -> None:
    """Test TiktokenTokenCounter smoothly falls back to heuristic counter when not installed."""
    counter = TiktokenTokenCounter(model_or_encoding="cl100k_base", allow_fallback=True)
    count = counter.count_tokens("Testing token count fallback mechanism")
    assert count > 0


@pytest.mark.asyncio
async def test_reconstruction_pipeline_with_citations_and_temporal_anchors(
    reconstruction_engine: ContextReconstructionEngine,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test complete 8-stage context reconstruction with verified citations."""
    now = datetime.datetime.now(datetime.UTC)

    m1 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="AMARA uses Python 3.12 with Pydantic v2 schemas and strict Mypy typing.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="architect",
        confidence=0.98,
        importance=0.90,
        asserted_at=now - datetime.timedelta(days=1),
    )
    m2 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="PostgreSQL 16 with pgvector is used for persistent cognitive memory storage.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="dba",
        confidence=0.95,
        importance=0.85,
        asserted_at=now,
    )

    await repo.store(m1)
    await repo.store(m2)

    result = await reconstruction_engine.reconstruct(
        query="What language and database does AMARA use?",
        tenant_id="tenant_acme",
        budget=ContextBudget(max_tokens=1000, system_reserved_tokens=100),
    )

    assert result.abstention_recommended is False
    assert result.abstention_reason is None
    assert result.candidates_packed >= 1
    assert len(result.citations) >= 1
    assert result.total_tokens_used > 0
    assert result.total_tokens_used <= 1000

    # Verify citation formatting
    first_cit = result.citations[0]
    assert first_cit.citation_tag == "[REF-1]"
    assert first_cit.source_id is not None
    assert "Asserted:" in first_cit.temporal_anchor

    # Verify formatted context contains citations
    assert "[REF-1]" in result.formatted_context
    assert "### AMARA Verified Cognitive Memory Context" in result.formatted_context


@pytest.mark.asyncio
async def test_reconstruction_token_budget_packing_stops_when_full(
    reconstruction_engine: ContextReconstructionEngine,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that context reconstruction strictly stops packing when budget is reached."""
    now = datetime.datetime.now(datetime.UTC)

    # Store 5 large memories
    for i in range(5):
        rec = MemoryRecord.create(
            tenant_id="tenant_acme",
            content=(
                f"Detailed specification report section {i}: "
                + "The cognitive memory framework provides adaptive lifecycle management, " * 5
            ),
            memory_type=MemoryCategory.SEMANTIC,
            author_id="user_1",
            confidence=0.9,
            importance=0.8,
            asserted_at=now,
        )
        await repo.store(rec)

    # Very small budget: 120 max tokens, 40 reserved = 80 tokens available
    tight_budget = ContextBudget(max_tokens=120, system_reserved_tokens=40)

    result = await reconstruction_engine.reconstruct(
        query="adaptive lifecycle management report",
        tenant_id="tenant_acme",
        budget=tight_budget,
    )

    # Total tokens must not exceed budget
    assert result.total_tokens_used <= tight_budget.max_tokens
    # Some candidates were omitted due to budget ceiling
    assert result.candidates_omitted_budget > 0
    assert result.candidates_packed < 5


@pytest.mark.asyncio
async def test_reconstruction_redundancy_removal(
    reconstruction_engine: ContextReconstructionEngine,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that near-duplicate retrieved results are filtered out to save budget."""
    now = datetime.datetime.now(datetime.UTC)

    # Two virtually identical records
    m1 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Redis cache is running on port 6379 in production.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="ops",
        asserted_at=now,
    )
    m2 = MemoryRecord.create(
        tenant_id="tenant_acme",
        content="Redis cache is running on port 6379 in production cluster.",
        memory_type=MemoryCategory.SEMANTIC,
        author_id="ops",
        asserted_at=now,
    )

    await repo.store(m1)
    await repo.store(m2)

    result = await reconstruction_engine.reconstruct(
        query="Redis cache port production",
        tenant_id="tenant_acme",
    )

    # Exactly one should be packed; the other omitted as redundant
    assert result.candidates_packed == 1
    assert result.candidates_omitted_redundant == 1


@pytest.mark.asyncio
async def test_reconstruction_abstention_on_unrelated_query(
    reconstruction_engine: ContextReconstructionEngine,
    repo: InMemoryMemoryRepository,
) -> None:
    """Test that abstention_recommended is True when query has zero or low relevance."""
    # Empty repo -> 0 candidates
    result_empty = await reconstruction_engine.reconstruct(
        query="What is the quantum state of the particle?",
        tenant_id="tenant_empty",
    )
    assert result_empty.abstention_recommended is True
    assert "No relevant memory records found" in (result_empty.abstention_reason or "")
