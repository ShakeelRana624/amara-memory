"""Bidirectional mappers between AMARA domain models and SQLAlchemy ORM entities."""

from __future__ import annotations

from amara.enums import (
    LifecycleStatus,
    MemoryCategory,
    MemoryEventType,
    ProvenanceSourceType,
    RelationType,
)
from amara.models.event import MemoryEvent
from amara.models.evidence import MemoryEvidence
from amara.models.record import MemoryRecord
from amara.models.relationship import MemoryRelationship
from amara.models.source import MemorySource
from amara.models.temporal import TemporalValidity
from amara.storage.schema import (
    MemoryEventORM,
    MemoryRecordORM,
    MemoryRelationshipORM,
)


def memory_record_to_orm(record: MemoryRecord) -> MemoryRecordORM:
    """Convert a MemoryRecord domain model to MemoryRecordORM."""
    evidence_dicts = [
        {
            "evidence_id": str(e.evidence_id),
            "source_reference": e.source_reference,
            "raw_payload": e.raw_payload,
            "confidence_score": e.confidence_score,
            "verified": e.verified,
            "recorded_at": e.recorded_at.isoformat(),
            "metadata": dict(e.metadata),
        }
        for e in record.evidence
    ]

    return MemoryRecordORM(
        id=record.id,
        tenant_id=record.tenant_id,
        namespace=record.namespace,
        memory_type=record.memory_type.value,
        status=record.status.value,
        original_content=record.original_content,
        normalized_content=record.normalized_content,
        source_id=record.source.source_id,
        source_type=record.source.source_type.value,
        author_id=record.source.author_id,
        session_id=record.source.session_id,
        source_event_id=record.source.source_event_id,
        content_hash=record.source.content_hash,
        extractor_signature=record.source.extractor_signature,
        source_metadata=dict(record.source.metadata),
        confidence=record.confidence,
        importance=record.importance,
        asserted_at=record.temporal.asserted_at,
        valid_from=record.temporal.valid_from,
        valid_to=record.temporal.valid_to,
        version=record.version,
        root_id=record.root_id,
        parent_ids=list(record.parent_ids),
        embedding=record.embedding,
        embedding_model_id=record.embedding_model_id,
        metadata_payload=dict(record.metadata),
        evidence_payload=evidence_dicts,
        access_count=record.access_count,
        utility_score=record.utility_score,
        last_accessed_at=record.last_accessed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        deleted_at=None,
    )


def orm_to_memory_record(orm: MemoryRecordORM) -> MemoryRecord:
    """Convert a MemoryRecordORM entity to MemoryRecord domain model."""
    source = MemorySource(
        source_id=orm.source_id,
        source_type=ProvenanceSourceType(orm.source_type),
        author_id=orm.author_id,
        session_id=orm.session_id,
        source_event_id=orm.source_event_id,
        content_hash=orm.content_hash,
        extractor_signature=orm.extractor_signature,
        metadata=dict(orm.source_metadata or {}),
    )

    temporal = TemporalValidity(
        asserted_at=orm.asserted_at,
        valid_from=orm.valid_from,
        valid_to=orm.valid_to,
    )

    evidence_list: list[MemoryEvidence] = []
    for item in orm.evidence_payload or []:
        evidence_list.append(MemoryEvidence.model_validate(item))

    return MemoryRecord(
        id=orm.id,
        tenant_id=orm.tenant_id,
        namespace=orm.namespace,
        memory_type=MemoryCategory(orm.memory_type),
        status=LifecycleStatus(orm.status),
        original_content=orm.original_content,
        normalized_content=orm.normalized_content,
        source=source,
        evidence=tuple(evidence_list),
        confidence=orm.confidence,
        importance=orm.importance,
        temporal=temporal,
        version=orm.version,
        root_id=orm.root_id,
        parent_ids=tuple(orm.parent_ids or []),
        embedding=orm.embedding,
        embedding_model_id=orm.embedding_model_id,
        metadata=dict(orm.metadata_payload or {}),
        access_count=orm.access_count,
        utility_score=orm.utility_score,
        last_accessed_at=orm.last_accessed_at,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def relationship_to_orm(rel: MemoryRelationship) -> MemoryRelationshipORM:
    """Convert MemoryRelationship domain model to ORM entity."""
    return MemoryRelationshipORM(
        relationship_id=rel.relationship_id,
        tenant_id=rel.tenant_id,
        source_id=rel.source_id,
        target_id=rel.target_id,
        relation_type=rel.relation_type.value,
        weight=rel.weight,
        bidirectional=rel.bidirectional,
        metadata_payload=dict(rel.metadata),
        created_at=rel.created_at,
    )


def orm_to_relationship(orm: MemoryRelationshipORM) -> MemoryRelationship:
    """Convert MemoryRelationshipORM entity to domain model."""
    return MemoryRelationship(
        relationship_id=orm.relationship_id,
        tenant_id=orm.tenant_id,
        source_id=orm.source_id,
        target_id=orm.target_id,
        relation_type=RelationType(orm.relation_type),
        weight=orm.weight,
        bidirectional=orm.bidirectional,
        metadata=dict(orm.metadata_payload or {}),
        created_at=orm.created_at,
    )


def event_to_orm(event: MemoryEvent) -> MemoryEventORM:
    """Convert MemoryEvent domain model to ORM entity."""
    return MemoryEventORM(
        event_id=event.event_id,
        tenant_id=event.tenant_id,
        namespace=event.namespace,
        memory_id=event.memory_id,
        event_type=event.event_type.value,
        timestamp=event.timestamp,
        payload=dict(event.payload),
    )


def orm_to_event(orm: MemoryEventORM) -> MemoryEvent:
    """Convert MemoryEventORM entity to domain model."""
    return MemoryEvent(
        event_id=orm.event_id,
        tenant_id=orm.tenant_id,
        namespace=orm.namespace,
        memory_id=orm.memory_id,
        event_type=MemoryEventType(orm.event_type),
        timestamp=orm.timestamp,
        payload=dict(orm.payload or {}),
    )
