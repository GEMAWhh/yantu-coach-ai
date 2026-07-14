"""mastery evidence and snapshots

Revision ID: 0005_mastery_state_machine
Revises: 0004_knowledge_model
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_mastery_state_machine"
down_revision: str | None = "0004_knowledge_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVIDENCE_TYPES = (
    "'reading','self_explanation','closed_book_recall','basic_question',"
    "'variant_question','integrated_question','interval_test','repeat_deep_cause'"
)


def upgrade() -> None:
    op.create_table(
        "mastery_evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(length=60), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Integer(), nullable=True),
        sa.Column("hint_level", sa.Integer(), nullable=True),
        sa.Column("is_original", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(f"evidence_type IN ({EVIDENCE_TYPES})", name="ck_mastery_evidence_type"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="ck_mastery_score"
        ),
        sa.CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)",
            name="ck_mastery_accuracy",
        ),
        sa.CheckConstraint("sample_count >= 0", name="ck_mastery_sample_count"),
    )
    op.create_index(
        "ix_mastery_evidence_knowledge_node_id", "mastery_evidence", ["knowledge_node_id"]
    )
    op.create_index("ix_mastery_evidence_evidence_type", "mastery_evidence", ["evidence_type"])
    op.create_index("ix_mastery_evidence_occurred_at", "mastery_evidence", ["occurred_at"])

    op.create_table(
        "mastery_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=False,
        ),
        sa.Column("previous_stage", sa.Integer(), nullable=False),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("recall_score", sa.Integer(), nullable=True),
        sa.Column("basic_score", sa.Integer(), nullable=True),
        sa.Column("variant_score", sa.Integer(), nullable=True),
        sa.Column("transfer_score", sa.Integer(), nullable=True),
        sa.Column("retention_score", sa.Integer(), nullable=True),
        sa.Column("repeat_error_rate", sa.Integer(), nullable=True),
        sa.Column("confidence_calibration", sa.Integer(), nullable=True),
        sa.Column("missing_link", sa.String(length=200), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("transition_reason", sa.Text(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("computed_metrics_json", sa.JSON(), nullable=False),
        sa.Column("blocking_reasons_json", sa.JSON(), nullable=False),
        sa.Column("remediation_json", sa.JSON(), nullable=True),
        sa.Column("actor_type", sa.String(length=40), nullable=False, server_default="system"),
        sa.CheckConstraint("stage >= 0 AND stage <= 8", name="ck_mastery_snapshot_stage"),
        sa.CheckConstraint(
            "previous_stage >= 0 AND previous_stage <= 8",
            name="ck_mastery_snapshot_previous_stage",
        ),
    )
    op.create_index(
        "ix_mastery_snapshots_knowledge_node_id", "mastery_snapshots", ["knowledge_node_id"]
    )
    op.create_index("ix_mastery_snapshots_stage", "mastery_snapshots", ["stage"])
    op.create_index("ix_mastery_snapshots_rule_version", "mastery_snapshots", ["rule_version"])
    op.create_index("ix_mastery_snapshots_evaluated_at", "mastery_snapshots", ["evaluated_at"])


def downgrade() -> None:
    op.drop_index("ix_mastery_snapshots_evaluated_at", table_name="mastery_snapshots")
    op.drop_index("ix_mastery_snapshots_rule_version", table_name="mastery_snapshots")
    op.drop_index("ix_mastery_snapshots_stage", table_name="mastery_snapshots")
    op.drop_index("ix_mastery_snapshots_knowledge_node_id", table_name="mastery_snapshots")
    op.drop_table("mastery_snapshots")
    op.drop_index("ix_mastery_evidence_occurred_at", table_name="mastery_evidence")
    op.drop_index("ix_mastery_evidence_evidence_type", table_name="mastery_evidence")
    op.drop_index("ix_mastery_evidence_knowledge_node_id", table_name="mastery_evidence")
    op.drop_table("mastery_evidence")
