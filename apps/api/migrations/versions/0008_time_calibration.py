"""time calibration

Revision ID: 0008_time_calibration
Revises: 0007_review_scheduler
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_time_calibration"
down_revision: str | None = "0007_review_scheduler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "time_coefficients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("task_type", sa.String(length=60), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("coefficient", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overtime_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_ratio", sa.Float(), nullable=True),
        sa.Column("last_estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("last_actual_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "last_task_result_id",
            sa.String(length=36),
            sa.ForeignKey("task_results.id"),
            nullable=True,
        ),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("rationale_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "coefficient >= 0.6 AND coefficient <= 1.8", name="ck_time_coefficients_bounds"
        ),
        sa.CheckConstraint("sample_count >= 0", name="ck_time_coefficients_sample_count"),
        sa.CheckConstraint("overtime_streak >= 0", name="ck_time_coefficients_overtime_streak"),
        sa.UniqueConstraint(
            "subject_id", "task_type", "difficulty", name="uq_time_coefficients_scope"
        ),
    )
    op.create_index("ix_time_coefficients_subject_id", "time_coefficients", ["subject_id"])
    op.create_index("ix_time_coefficients_task_type", "time_coefficients", ["task_type"])
    op.create_index("ix_time_coefficients_difficulty", "time_coefficients", ["difficulty"])
    op.create_index("ix_time_coefficients_rule_version", "time_coefficients", ["rule_version"])

    op.create_table(
        "time_adjustments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "coefficient_id",
            sa.String(length=36),
            sa.ForeignKey("time_coefficients.id"),
            nullable=False,
        ),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column(
            "task_result_id", sa.String(length=36), sa.ForeignKey("task_results.id"), nullable=False
        ),
        sa.Column("subject_id", sa.String(length=36), nullable=False),
        sa.Column("task_type", sa.String(length=60), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("actual_minutes", sa.Integer(), nullable=False),
        sa.Column("raw_ratio", sa.Float(), nullable=True),
        sa.Column("applied_ratio", sa.Float(), nullable=True),
        sa.Column("previous_coefficient", sa.Float(), nullable=False),
        sa.Column("new_coefficient", sa.Float(), nullable=False),
        sa.Column("ignored", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ignore_reason", sa.String(length=80), nullable=True),
        sa.Column("overtime", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("suggested_split", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rule_version", sa.String(length=80), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.CheckConstraint("estimated_minutes >= 0", name="ck_time_adjustments_estimated_minutes"),
        sa.CheckConstraint("actual_minutes >= 0", name="ck_time_adjustments_actual_minutes"),
        sa.UniqueConstraint("task_result_id", name="uq_time_adjustments_task_result"),
    )
    op.create_index("ix_time_adjustments_coefficient_id", "time_adjustments", ["coefficient_id"])
    op.create_index("ix_time_adjustments_task_result_id", "time_adjustments", ["task_result_id"])
    op.create_index("ix_time_adjustments_subject_id", "time_adjustments", ["subject_id"])
    op.create_index("ix_time_adjustments_task_type", "time_adjustments", ["task_type"])
    op.create_index("ix_time_adjustments_difficulty", "time_adjustments", ["difficulty"])
    op.create_index("ix_time_adjustments_rule_version", "time_adjustments", ["rule_version"])
    op.create_index("ix_time_adjustments_occurred_at", "time_adjustments", ["occurred_at"])
    op.create_index("ix_time_adjustments_request_id", "time_adjustments", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_time_adjustments_request_id", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_occurred_at", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_rule_version", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_difficulty", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_task_type", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_subject_id", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_task_result_id", table_name="time_adjustments")
    op.drop_index("ix_time_adjustments_coefficient_id", table_name="time_adjustments")
    op.drop_table("time_adjustments")
    op.drop_index("ix_time_coefficients_rule_version", table_name="time_coefficients")
    op.drop_index("ix_time_coefficients_difficulty", table_name="time_coefficients")
    op.drop_index("ix_time_coefficients_task_type", table_name="time_coefficients")
    op.drop_index("ix_time_coefficients_subject_id", table_name="time_coefficients")
    op.drop_table("time_coefficients")
