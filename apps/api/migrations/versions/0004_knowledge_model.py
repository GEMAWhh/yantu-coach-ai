"""knowledge nodes and edges

Revision ID: 0004_knowledge_model
Revises: 0003_localstorage_import
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_knowledge_model"
down_revision: str | None = "0003_localstorage_import"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NODE_TYPES = "'subject','module','chapter','knowledge'"
RELATION_TYPES = (
    "'belongs_to','prerequisite','similar_to','confused_with','co_tested','transforms_to'"
)


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column(
            "parent_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("node_type", sa.String(length=40), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=True),
        sa.Column("exam_frequency", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.CheckConstraint(f"node_type IN ({NODE_TYPES})", name="ck_knowledge_nodes_node_type"),
    )
    op.create_index("ix_knowledge_nodes_code", "knowledge_nodes", ["code"], unique=True)
    op.create_index("ix_knowledge_nodes_parent_id", "knowledge_nodes", ["parent_id"])
    op.create_index("ix_knowledge_nodes_subject_id", "knowledge_nodes", ["subject_id"])
    op.create_index("ix_knowledge_nodes_node_type", "knowledge_nodes", ["node_type"])
    op.create_index("ix_knowledge_nodes_status", "knowledge_nodes", ["status"])
    op.create_index("ix_knowledge_nodes_is_deleted", "knowledge_nodes", ["is_deleted"])

    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=False,
        ),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="user"),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("source_node_id <> target_node_id", name="ck_knowledge_edges_not_self"),
        sa.CheckConstraint(
            f"relation_type IN ({RELATION_TYPES})", name="ck_knowledge_edges_relation_type"
        ),
        sa.UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="uq_knowledge_edges_relation",
        ),
    )
    op.create_index("ix_knowledge_edges_source_node_id", "knowledge_edges", ["source_node_id"])
    op.create_index("ix_knowledge_edges_target_node_id", "knowledge_edges", ["target_node_id"])
    op.create_index("ix_knowledge_edges_relation_type", "knowledge_edges", ["relation_type"])
    op.create_index("ix_knowledge_edges_is_deleted", "knowledge_edges", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_edges_is_deleted", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_relation_type", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_target_node_id", table_name="knowledge_edges")
    op.drop_index("ix_knowledge_edges_source_node_id", table_name="knowledge_edges")
    op.drop_table("knowledge_edges")
    op.drop_index("ix_knowledge_nodes_is_deleted", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_status", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_node_type", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_subject_id", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_parent_id", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_code", table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
