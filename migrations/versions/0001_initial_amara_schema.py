"""Initial AMARA schema with pgvector, HNSW, audit history, and RLS.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-13 13:20:00.000000+00:00

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import pgvector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 2. Create memory_records table
    op.create_table(
        "memory_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("namespace", sa.String(128), nullable=False, server_default="default"),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("source_id", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("author_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.String(128), nullable=True),
        sa.Column("source_event_id", sa.String(128), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("extractor_signature", sa.String(128), nullable=True),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("asserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("root_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "parent_ids",
            sa.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("embedding_model_id", sa.String(128), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"
        ),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("utility_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes on memory_records
    op.create_index("idx_memory_records_tenant_id", "memory_records", ["tenant_id"])
    op.create_index("idx_memory_records_namespace", "memory_records", ["namespace"])
    op.create_index("idx_memory_records_type", "memory_records", ["memory_type"])
    op.create_index("idx_memory_records_status", "memory_records", ["status"])
    op.create_index("idx_memory_records_root_id", "memory_records", ["root_id"])
    op.create_index(
        "idx_memory_tenant_modality",
        "memory_records",
        ["tenant_id", "namespace", "memory_type", "status"],
    )
    op.create_index(
        "idx_memory_temporal",
        "memory_records",
        ["tenant_id", "valid_from", "valid_to"],
    )
    op.create_index(
        "idx_memory_metadata_gin",
        "memory_records",
        ["metadata"],
        postgresql_using="gin",
    )
    # HNSW Index for cosine distance fast approximate nearest neighbor search
    op.execute(
        "CREATE INDEX idx_memory_embedding_hnsw ON memory_records "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # 3. Create memory_relationships table
    op.create_table(
        "memory_relationships",
        sa.Column("relationship_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memory_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memory_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("bidirectional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("idx_rel_tenant_id", "memory_relationships", ["tenant_id"])
    op.create_index(
        "idx_rel_tenant_source", "memory_relationships", ["tenant_id", "source_id", "relation_type"]
    )
    op.create_index(
        "idx_rel_tenant_target", "memory_relationships", ["tenant_id", "target_id", "relation_type"]
    )

    # 4. Create memory_version_history table
    op.create_table(
        "memory_version_history",
        sa.Column("history_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "memory_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("memory_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("changed_by", sa.String(128), nullable=False),
        sa.Column("change_reason", sa.String(256), nullable=True),
    )
    op.create_index("idx_history_tenant_id", "memory_version_history", ["tenant_id"])
    op.create_index(
        "idx_history_tenant_memory_version",
        "memory_version_history",
        ["tenant_id", "memory_id", "version"],
    )

    # 5. Create memory_events table
    op.create_table(
        "memory_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("namespace", sa.String(128), nullable=False),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
    )
    op.create_index("idx_events_tenant_id", "memory_events", ["tenant_id"])
    op.create_index("idx_events_tenant_timestamp", "memory_events", ["tenant_id", "timestamp"])
    op.create_index("idx_events_tenant_memory", "memory_events", ["tenant_id", "memory_id"])

    # 6. Configure Row-Level Security (RLS)
    # Enable RLS policies for tenant isolation
    for tbl in [
        "memory_records",
        "memory_relationships",
        "memory_version_history",
        "memory_events",
    ]:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation_{tbl} ON {tbl} "
            f"FOR ALL USING ("
            f"  tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '') "
            f"  OR current_setting('app.bypass_rls', true) = 'on'"
            f");"
        )


def downgrade() -> None:
    # Drop tables and policies
    for tbl in [
        "memory_events",
        "memory_version_history",
        "memory_relationships",
        "memory_records",
    ]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{tbl} ON {tbl};")
        op.drop_table(tbl)
