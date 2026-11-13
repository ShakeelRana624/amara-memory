"""Unified asynchronous public developer SDK for AMARA cognitive memory."""

from __future__ import annotations

import datetime
from collections import defaultdict
from collections.abc import Sequence
from types import TracebackType
from typing import Any
from uuid import UUID, uuid4

from amara.context.engine import ContextReconstructionEngine
from amara.context.types import ContextBudget, ContextReconstructionConfig, ReconstructedContext
from amara.contracts.query import QueryFilter, QuerySpec
from amara.contracts.repository import MemoryRepository
from amara.enums import LifecycleStatus, MemoryCategory
from amara.exceptions import MemoryNotFoundError
from amara.intelligence.pipeline import MemoryIngestionPipeline
from amara.intelligence.providers.rule_based import DeterministicRuleEmbeddingProvider
from amara.lifecycle.manager import MemoryLifecycleManager
from amara.lifecycle.types import ConsolidationPolicy, RetentionPolicy
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.retrieval.engine import MemoryRetrievalEngine
from amara.retrieval.types import RetrievalStrategy
from amara.sdk.config import MemoryConfig
from amara.sdk.types import (
    EngineStats,
    InspectionResult,
    MemoryItem,
    RecallItem,
    RecallResponse,
)
from amara.storage.database import DatabaseManager
from amara.storage.memory import InMemoryMemoryRepository
from amara.storage.postgres import PostgresMemoryRepository


def _coerce_uuid(val: UUID | str) -> UUID:
    """Safely coerce string or UUID into UUID."""
    if isinstance(val, UUID):
        return val
    return UUID(str(val))


class MemoryEngine:
    """The developer-facing asynchronous cognitive memory engine for AMARA.

    Provides a clean, unified interface for remembering, recalling, consolidating,
    updating, forgetting, and reconstructing context.
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        repository: MemoryRepository | None = None,
    ) -> None:
        self.config = config or MemoryConfig.from_env()
        self._db_manager: DatabaseManager | None = None
        self._repository = repository
        self._initialized = False

        # Internal subsystem handles (initialized upon async init)
        self._ingestion_pipeline: MemoryIngestionPipeline | None = None
        self._retrieval_engine: MemoryRetrievalEngine | None = None
        self._lifecycle_manager: MemoryLifecycleManager | None = None
        self._reconstruction_engine: ContextReconstructionEngine | None = None

    async def __aenter__(self) -> MemoryEngine:
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def initialize(self) -> None:
        """Initialize the storage engine, database connection pools, and subsystems."""
        if self._initialized:
            return

        if self._repository is None:
            if self.config.storage_backend == "postgres":
                if not self.config.database_url:
                    raise ValueError(
                        "database_url must be provided when storage_backend is 'postgres'."
                    )
                self._db_manager = DatabaseManager(
                    self.config.database_url,
                    pool_size=self.config.db_pool_size,
                    max_overflow=self.config.db_max_overflow,
                )
                await self._db_manager.initialize()
                self._repository = PostgresMemoryRepository(self._db_manager)
            else:
                self._repository = InMemoryMemoryRepository()

        await self._repository.initialize()

        # Wire intelligence and provider subsystems
        embedding_provider = DeterministicRuleEmbeddingProvider()

        self._ingestion_pipeline = MemoryIngestionPipeline(
            repository=self._repository,
            embedding_provider=embedding_provider,
        )

        self._retrieval_engine = MemoryRetrievalEngine(
            repository=self._repository,
            embedding_provider=embedding_provider,
            decay_half_life_days=self.config.decay_half_life_days,
        )

        retention_pol = RetentionPolicy(
            decay_half_life_days=self.config.decay_half_life_days,
            auto_archive_expired=self.config.auto_archive_expired,
        )
        consolidation_pol = ConsolidationPolicy(
            similarity_threshold=self.config.similarity_threshold,
        )

        self._lifecycle_manager = MemoryLifecycleManager(
            repository=self._repository,
            retention_policy=retention_pol,
            consolidation_policy=consolidation_pol,
        )

        reconstruction_cfg = ContextReconstructionConfig(
            abstention_threshold=self.config.abstention_threshold,
        )
        self._reconstruction_engine = ContextReconstructionEngine(
            retrieval_engine=self._retrieval_engine,
            config=reconstruction_cfg,
        )

        self._initialized = True

    async def close(self) -> None:
        """Gracefully release storage connection pools and resources."""
        if self._repository is not None:
            await self._repository.close()
        if self._db_manager is not None:
            await self._db_manager.close()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if (
            not self._initialized
            or self._repository is None
            or self._ingestion_pipeline is None
            or self._retrieval_engine is None
            or self._lifecycle_manager is None
            or self._reconstruction_engine is None
        ):
            raise RuntimeError(
                "MemoryEngine is not initialized. Call 'await engine.initialize()' "
                "or use 'async with engine:' before executing operations."
            )

    # -----------------------------------------------------------------------
    # Core Public SDK Operations
    # -----------------------------------------------------------------------

    async def remember(
        self,
        content: str,
        author_id: str = "user",
        memory_type: MemoryCategory | str | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        tenant_id: str | None = None,
        namespace: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        valid_from: datetime.datetime | None = None,
        valid_to: datetime.datetime | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> MemoryItem:
        """Ingest, normalize, extract, and store a new memory proposition."""
        self._ensure_initialized()
        assert self._ingestion_pipeline is not None
        assert self._repository is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        effective_ns = namespace or self.config.default_namespace

        cat = MemoryCategory(memory_type) if memory_type else None
        source_id = f"src_{uuid4().hex[:12]}"

        # Ingest text through ingestion intelligence pipeline
        result = await self._ingestion_pipeline.ingest_text(
            content=content,
            tenant_id=effective_tenant,
            source_id=source_id,
            author_id=author_id,
            namespace=effective_ns,
            session_id=session_id,
            explicit_category=cat,
            valid_from=valid_from,
            valid_to=valid_to,
            metadata=metadata or {},
        )

        # Retrieve stored primary record
        primary_record: MemoryRecord | None = None
        if result.stored_records:
            primary_record = result.stored_records[0]
        elif result.reinforced_records:
            primary_record = await self._repository.get_by_id(
                effective_tenant, result.reinforced_records[0]
            )

        if primary_record is None:
            # Direct creation fallback if pipeline filtered everything
            now = datetime.datetime.now(datetime.UTC)
            cat_final = cat or MemoryCategory.SEMANTIC
            primary_record = MemoryRecord.create(
                tenant_id=effective_tenant,
                namespace=effective_ns,
                content=content,
                memory_type=cat_final,
                author_id=author_id,
                confidence=confidence,
                importance=importance,
                session_id=session_id,
                valid_from=valid_from or now,
                valid_to=valid_to,
                metadata=metadata or {},
            )
            await self._repository.store(primary_record)

        # Attach custom evidence if provided
        if evidence:
            for ev_data in evidence:
                ev_obj = MemoryEvidence(
                    source_reference=str(ev_data.get("source_reference", "custom_evidence")),
                    raw_payload=str(ev_data.get("raw_payload", "")),
                    confidence_score=float(ev_data.get("confidence_score", 1.0)),
                )
                primary_record.add_evidence(ev_obj)

        return MemoryItem.from_record(primary_record)

    async def recall(
        self,
        query: str,
        tenant_id: str | None = None,
        namespace: str | None = None,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
        top_k: int = 10,
        memory_types: Sequence[MemoryCategory] | None = None,
        valid_at: datetime.datetime | None = None,
        reference_time: datetime.datetime | None = None,
        include_historical: bool = False,
    ) -> RecallResponse:
        """Search and retrieve memories matching query across hybrid channels."""
        self._ensure_initialized()
        assert self._retrieval_engine is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        effective_ns = namespace or self.config.default_namespace
        strat = RetrievalStrategy(strategy) if isinstance(strategy, str) else strategy

        response = await self._retrieval_engine.retrieve(
            query=query,
            tenant_id=effective_tenant,
            namespace=effective_ns,
            strategy=strat,
            top_k=top_k,
            memory_types=memory_types,
            valid_at=valid_at,
            reference_time=reference_time,
            include_historical=include_historical,
        )

        recall_items: list[RecallItem] = []
        for r in response.results:
            # Construct a clean MemoryItem from search result
            item = MemoryItem(
                id=r.memory_id,
                tenant_id=effective_tenant,
                namespace=effective_ns,
                content=r.content,
                normalized_content=r.normalized_content,
                memory_type=r.memory_type,
                status=r.lifecycle_status,
                confidence=r.confidence,
                importance=r.importance,
                source_id=r.source_id,
                author_id=r.author_id,
                session_id=None,
                asserted_at=r.temporal_validity.asserted_at,
                valid_from=r.temporal_validity.valid_from,
                valid_to=r.temporal_validity.valid_to,
                version=1,
                root_id=r.memory_id,
                parent_ids=(),
                metadata=dict(r.metadata),
                created_at=r.timestamp,
                updated_at=r.timestamp,
            )
            recall_items.append(
                RecallItem(
                    item=item,
                    relevance_score=r.relevance_score,
                    confidence=r.confidence,
                    match_explanation=r.match_explanation,
                )
            )

        return RecallResponse(
            query=query,
            tenant_id=effective_tenant,
            namespace=effective_ns,
            results=tuple(recall_items),
            total_candidates=response.total_candidates,
            latency_ms=response.latency_ms,
        )

    async def update(
        self,
        memory_id: UUID | str,
        new_content: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> MemoryItem:
        """Update a memory record's content or metadata cleanly."""
        self._ensure_initialized()
        assert self._lifecycle_manager is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        mid = _coerce_uuid(memory_id)

        updated_record = await self._lifecycle_manager.update(
            tenant_id=effective_tenant,
            memory_id=mid,
            new_content=new_content,
            metadata_updates=metadata_updates,
        )
        return MemoryItem.from_record(updated_record)

    async def forget(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
        hard: bool = False,
        cascade: bool = False,
        force: bool = False,
    ) -> bool:
        """Delete a memory record using soft tombstone or physical purge."""
        self._ensure_initialized()
        assert self._lifecycle_manager is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        mid = _coerce_uuid(memory_id)

        return await self._lifecycle_manager.delete(
            tenant_id=effective_tenant,
            memory_id=mid,
            hard=hard,
            cascade=cascade,
            force=force,
        )

    async def archive(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
        force: bool = False,
    ) -> MemoryItem:
        """Transition a memory record to cold ARCHIVED status."""
        self._ensure_initialized()
        assert self._lifecycle_manager is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        mid = _coerce_uuid(memory_id)

        archived_record = await self._lifecycle_manager.archive(
            tenant_id=effective_tenant,
            memory_id=mid,
            force=force,
        )
        return MemoryItem.from_record(archived_record)

    async def restore(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
    ) -> MemoryItem:
        """Restore an archived, superseded, or expired record back to ACTIVE status."""
        self._ensure_initialized()
        assert self._lifecycle_manager is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        mid = _coerce_uuid(memory_id)

        restored_record = await self._lifecycle_manager.restore(
            tenant_id=effective_tenant,
            memory_id=mid,
        )
        return MemoryItem.from_record(restored_record)

    async def consolidate(
        self,
        tenant_id: str | None = None,
        namespace: str | None = None,
    ) -> list[MemoryItem]:
        """Trigger knowledge consolidation clustering and synthesis."""
        self._ensure_initialized()
        assert self._lifecycle_manager is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        effective_ns = namespace or self.config.default_namespace

        results = await self._lifecycle_manager.consolidate(
            tenant_id=effective_tenant,
            namespace=effective_ns,
        )
        return [MemoryItem.from_record(r.consolidated_record) for r in results]

    async def reconstruct(
        self,
        query: str,
        tenant_id: str | None = None,
        namespace: str | None = None,
        budget: ContextBudget | int | None = None,
        strategy: RetrievalStrategy | str = RetrievalStrategy.HYBRID,
    ) -> ReconstructedContext:
        """Reconstruct a token-bounded, citation-attributed context prompt block."""
        self._ensure_initialized()
        assert self._reconstruction_engine is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        effective_ns = namespace or self.config.default_namespace

        if isinstance(budget, int):
            effective_budget = ContextBudget(
                max_tokens=budget,
                system_reserved_tokens=self.config.system_reserved_tokens,
            )
        else:
            effective_budget = budget or ContextBudget(
                max_tokens=self.config.token_budget,
                system_reserved_tokens=self.config.system_reserved_tokens,
            )

        strat = RetrievalStrategy(strategy) if isinstance(strategy, str) else strategy

        return await self._reconstruction_engine.reconstruct(
            query=query,
            tenant_id=effective_tenant,
            namespace=effective_ns,
            budget=effective_budget,
            strategy=strat,
        )

    async def inspect(
        self,
        memory_id: UUID | str,
        tenant_id: str | None = None,
    ) -> InspectionResult:
        """Inspect a specific memory record, its derivation lineage, and relationships."""
        self._ensure_initialized()
        assert self._repository is not None

        effective_tenant = tenant_id or self.config.default_tenant_id
        mid = _coerce_uuid(memory_id)

        record = await self._repository.get_by_id(effective_tenant, mid)
        if record is None:
            raise MemoryNotFoundError(mid, tenant_id=effective_tenant)

        # Fetch parents
        parents: list[MemoryItem] = []
        for pid in record.parent_ids:
            parent_rec = await self._repository.get_by_id(effective_tenant, pid)
            if parent_rec is not None:
                parents.append(MemoryItem.from_record(parent_rec))

        # Fetch relationships
        relationships = await self._repository.get_relationships(effective_tenant, mid)
        rel_data = [
            {
                "id": str(r.relationship_id),
                "source_id": str(r.source_id),
                "target_id": str(r.target_id),
                "relation_type": r.relation_type.value,
                "weight": r.weight,
                "metadata": dict(r.metadata),
            }
            for r in relationships
        ]

        # Extract evidence
        ev_data = [
            {
                "id": str(ev.evidence_id),
                "source_reference": ev.source_reference,
                "raw_payload": ev.raw_payload,
                "confidence_score": ev.confidence_score,
                "timestamp": ev.recorded_at.isoformat(),
            }
            for ev in record.evidence
        ]

        return InspectionResult(
            record=MemoryItem.from_record(record),
            parents=tuple(parents),
            relationships=tuple(rel_data),
            evidence=tuple(ev_data),
        )

    async def stats(
        self,
        tenant_id: str | None = None,
        namespace: str | None = None,
    ) -> EngineStats:
        """Gather cognitive distribution and state machine metrics for tenant/workspace."""
        self._ensure_initialized()
        assert self._repository is not None

        effective_tenant = tenant_id or self.config.default_tenant_id

        # Query all records including decaying, consolidated, and archived
        spec = QuerySpec(
            filter=QueryFilter(
                tenant_id=effective_tenant,
                namespace=namespace,
                statuses=(
                    LifecycleStatus.ACTIVE,
                    LifecycleStatus.DECAYING,
                    LifecycleStatus.CONSOLIDATED,
                    LifecycleStatus.SUPERSEDED,
                    LifecycleStatus.ARCHIVED,
                ),
            ),
            top_k=5000,
            include_tombstoned=False,
        )
        records = await self._repository.query(spec)

        by_cat: dict[str, int] = defaultdict(int)
        by_stat: dict[str, int] = defaultdict(int)
        total_conf = 0.0
        total_imp = 0.0

        for r in records:
            by_cat[r.memory_type.value] += 1
            by_stat[r.status.value] += 1
            total_conf += r.confidence
            total_imp += r.importance

        count = len(records)
        avg_conf = (total_conf / count) if count > 0 else 0.0
        avg_imp = (total_imp / count) if count > 0 else 0.0

        return EngineStats(
            tenant_id=effective_tenant,
            namespace=namespace,
            total_memories=count,
            by_category=dict(by_cat),
            by_status=dict(by_stat),
            average_confidence=float(round(avg_conf, 4)),
            average_importance=float(round(avg_imp, 4)),
        )
