"""review scheduler

Revision ID: 0007_review_scheduler
Revises: 0006_goals_tasks
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_review_scheduler"
down_revision: str | None = "0006_goals_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVIEW_SCHEDULE_STATUSES = "'active','paused','completed','archived'"
REVIEW_RESULT_TYPES = "'pass','fail'"


def upgrade() -> None:
    op.create_table(
        "review_schedules",
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
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("current_stage", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False),
        sa.Column("pass_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fail_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_result_id", sa.String(length=36), nullable=True),
        sa.Column(
            "source_snapshot_id",
            sa.String(length=36),
            sa.ForeignKey("mastery_snapshots.id"),
            nullable=True,
        ),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("next_reason", sa.Text(), nullable=False),
        sa.CheckConstraint(
            f"status IN ({REVIEW_SCHEDULE_STATUSES})",
            name="ck_review_schedules_status",
        ),
        sa.CheckConstraint(
            "current_stage >= 0 AND current_stage <= 8",
            name="ck_review_schedules_current_stage",
        ),
        sa.CheckConstraint("interval_days >= 1", name="ck_review_schedules_interval_days"),
        sa.CheckConstraint("pass_streak >= 0", name="ck_review_schedules_pass_streak"),
        sa.CheckConstraint("fail_streak >= 0", name="ck_review_schedules_fail_streak"),
    )
    op.create_index(
        "ix_review_schedules_knowledge_node_id", "review_schedules", ["knowledge_node_id"]
    )
    op.create_index("ix_review_schedules_subject_id", "review_schedules", ["subject_id"])
    op.create_index("ix_review_schedules_current_stage", "review_schedules", ["current_stage"])
    op.create_index("ix_review_schedules_status", "review_schedules", ["status"])
    op.create_index("ix_review_schedules_due_at", "review_schedules", ["due_at"])
    op.create_index("ix_review_schedules_is_deleted", "review_schedules", ["is_deleted"])

    op.create_table(
        "review_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "schedule_id",
            sa.String(length=36),
            sa.ForeignKey("review_schedules.id"),
            nullable=False,
        ),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("result_type", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Integer(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("independent_timepoint", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "evidence_id",
            sa.String(length=36),
            sa.ForeignKey("mastery_evidence.id"),
            nullable=True,
        ),
        sa.Column(
            "snapshot_id",
            sa.String(length=36),
            sa.ForeignKey("mastery_snapshots.id"),
            nullable=True,
        ),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            f"result_type IN ({REVIEW_RESULT_TYPES})", name="ck_review_results_type"
        ),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_review_results_score",
        ),
        sa.CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)",
            name="ck_review_results_accuracy",
        ),
        sa.CheckConstraint("sample_count >= 0", name="ck_review_results_sample_count"),
        sa.CheckConstraint(
            "correct_count IS NULL OR correct_count >= 0",
            name="ck_review_results_correct_count",
        ),
        sa.UniqueConstraint("schedule_id", "idempotency_key", name="uq_review_results_idempotency"),
    )
    op.create_index("ix_review_results_schedule_id", "review_results", ["schedule_id"])
    op.create_index("ix_review_results_knowledge_node_id", "review_results", ["knowledge_node_id"])
    op.create_index("ix_review_results_occurred_at", "review_results", ["occurred_at"])
    op.create_index("ix_review_results_request_id", "review_results", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_review_results_request_id", table_name="review_results")
    op.drop_index("ix_review_results_occurred_at", table_name="review_results")
    op.drop_index("ix_review_results_knowledge_node_id", table_name="review_results")
    op.drop_index("ix_review_results_schedule_id", table_name="review_results")
    op.drop_table("review_results")
    op.drop_index("ix_review_schedules_is_deleted", table_name="review_schedules")
    op.drop_index("ix_review_schedules_due_at", table_name="review_schedules")
    op.drop_index("ix_review_schedules_status", table_name="review_schedules")
    op.drop_index("ix_review_schedules_current_stage", table_name="review_schedules")
    op.drop_index("ix_review_schedules_subject_id", table_name="review_schedules")
    op.drop_index("ix_review_schedules_knowledge_node_id", table_name="review_schedules")
    op.drop_table("review_schedules")
