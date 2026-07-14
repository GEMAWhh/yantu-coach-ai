"""goal recalculation history

Revision ID: 0011_goal_recalculation_history
Revises: 0010_wrongbook_domain
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_goal_recalculation_history"
down_revision: str | None = "0010_wrongbook_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goal_history_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("goal_id", sa.String(length=36), sa.ForeignKey("goals.id"), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("previous_progress", sa.Integer(), nullable=False),
        sa.Column("new_progress", sa.Integer(), nullable=False),
        sa.Column("previous_actual_minutes", sa.Integer(), nullable=False),
        sa.Column("new_actual_minutes", sa.Integer(), nullable=False),
        sa.Column("previous_risk_status", sa.String(length=40), nullable=False),
        sa.Column("new_risk_status", sa.String(length=40), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=False),
        sa.Column("new_status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("source_id", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            "previous_progress >= 0 AND previous_progress <= 100",
            name="ck_goal_history_previous_progress",
        ),
        sa.CheckConstraint(
            "new_progress >= 0 AND new_progress <= 100",
            name="ck_goal_history_new_progress",
        ),
        sa.CheckConstraint(
            "previous_actual_minutes >= 0",
            name="ck_goal_history_previous_actual_minutes",
        ),
        sa.CheckConstraint(
            "new_actual_minutes >= 0",
            name="ck_goal_history_new_actual_minutes",
        ),
    )
    op.create_index("ix_goal_history_events_goal_id", "goal_history_events", ["goal_id"])
    op.create_index("ix_goal_history_events_event_type", "goal_history_events", ["event_type"])
    op.create_index("ix_goal_history_events_request_id", "goal_history_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_goal_history_events_request_id", table_name="goal_history_events")
    op.drop_index("ix_goal_history_events_event_type", table_name="goal_history_events")
    op.drop_index("ix_goal_history_events_goal_id", table_name="goal_history_events")
    op.drop_table("goal_history_events")
