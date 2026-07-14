"""goals tasks and task results

Revision ID: 0006_goals_tasks
Revises: 0005_mastery_state_machine
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_goals_tasks"
down_revision: str | None = "0005_mastery_state_machine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GOAL_LEVELS = "'semester','quarter','month','week','day'"
GOAL_STATUSES = "'draft','active','completed','delayed','archived','cancelled'"
TASK_STATUSES = "'pending','in_progress','completed','skipped','withdrawn'"
TASK_RESULTS = "'completed','partial','wrong','unknown'"


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "parent_id",
            sa.String(length=36),
            sa.ForeignKey("goals.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("level", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_standard", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_status", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("adjustment_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(f"level IN ({GOAL_LEVELS})", name="ck_goals_level"),
        sa.CheckConstraint(f"status IN ({GOAL_STATUSES})", name="ck_goals_status"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="ck_goals_progress"),
        sa.CheckConstraint("estimated_minutes >= 0", name="ck_goals_estimated_minutes"),
        sa.CheckConstraint("actual_minutes >= 0", name="ck_goals_actual_minutes"),
    )
    op.create_index("ix_goals_parent_id", "goals", ["parent_id"])
    op.create_index("ix_goals_level", "goals", ["level"])
    op.create_index("ix_goals_subject_id", "goals", ["subject_id"])
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_is_deleted", "goals", ["is_deleted"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id"), nullable=True),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=True,
        ),
        sa.Column("wrong_record_id", sa.String(length=36), nullable=True),
        sa.Column("review_schedule_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("task_type", sa.String(length=60), nullable=False, server_default="study"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=True),
        sa.Column("cognitive_load", sa.String(length=40), nullable=True),
        sa.Column("current_stage", sa.Integer(), nullable=True),
        sa.Column("target_stage", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("completion_standard", sa.Text(), nullable=True),
        sa.Column(
            "prerequisite_status", sa.String(length=40), nullable=False, server_default="unknown"
        ),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.CheckConstraint(f"status IN ({TASK_STATUSES})", name="ck_tasks_status"),
        sa.CheckConstraint("estimated_minutes >= 0", name="ck_tasks_estimated_minutes"),
        sa.CheckConstraint(
            "current_stage IS NULL OR (current_stage >= 0 AND current_stage <= 8)",
            name="ck_tasks_current_stage",
        ),
        sa.CheckConstraint(
            "target_stage IS NULL OR (target_stage >= 0 AND target_stage <= 8)",
            name="ck_tasks_target_stage",
        ),
    )
    op.create_index("ix_tasks_goal_id", "tasks", ["goal_id"])
    op.create_index("ix_tasks_subject_id", "tasks", ["subject_id"])
    op.create_index("ix_tasks_knowledge_node_id", "tasks", ["knowledge_node_id"])
    op.create_index("ix_tasks_planned_date", "tasks", ["planned_date"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_is_deleted", "tasks", ["is_deleted"])

    op.create_table(
        "task_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("result_type", sa.String(length=40), nullable=False),
        sa.Column("completion_ratio", sa.Integer(), nullable=False),
        sa.Column("actual_minutes", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=True),
        sa.Column("correct_count", sa.Integer(), nullable=True),
        sa.Column("accuracy", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("hint_level", sa.Integer(), nullable=True),
        sa.Column("focus_level", sa.Integer(), nullable=True),
        sa.Column("difficulty_rating", sa.Integer(), nullable=True),
        sa.Column("problem_description", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.CheckConstraint(f"result_type IN ({TASK_RESULTS})", name="ck_task_results_type"),
        sa.CheckConstraint(
            "completion_ratio >= 0 AND completion_ratio <= 100",
            name="ck_task_results_completion_ratio",
        ),
        sa.CheckConstraint("actual_minutes >= 0", name="ck_task_results_actual_minutes"),
        sa.CheckConstraint(
            "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 100)",
            name="ck_task_results_accuracy",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_task_results_confidence",
        ),
        sa.CheckConstraint(
            "question_count IS NULL OR question_count >= 0",
            name="ck_task_results_question_count",
        ),
        sa.CheckConstraint(
            "correct_count IS NULL OR correct_count >= 0",
            name="ck_task_results_correct_count",
        ),
        sa.UniqueConstraint("task_id", "idempotency_key", name="uq_task_results_idempotency"),
    )
    op.create_index("ix_task_results_task_id", "task_results", ["task_id"])
    op.create_index("ix_task_results_confirmed_at", "task_results", ["confirmed_at"])
    op.create_index("ix_task_results_request_id", "task_results", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_task_results_request_id", table_name="task_results")
    op.drop_index("ix_task_results_confirmed_at", table_name="task_results")
    op.drop_index("ix_task_results_task_id", table_name="task_results")
    op.drop_table("task_results")
    op.drop_index("ix_tasks_is_deleted", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_planned_date", table_name="tasks")
    op.drop_index("ix_tasks_knowledge_node_id", table_name="tasks")
    op.drop_index("ix_tasks_subject_id", table_name="tasks")
    op.drop_index("ix_tasks_goal_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_goals_is_deleted", table_name="goals")
    op.drop_index("ix_goals_status", table_name="goals")
    op.drop_index("ix_goals_subject_id", table_name="goals")
    op.drop_index("ix_goals_level", table_name="goals")
    op.drop_index("ix_goals_parent_id", table_name="goals")
    op.drop_table("goals")
