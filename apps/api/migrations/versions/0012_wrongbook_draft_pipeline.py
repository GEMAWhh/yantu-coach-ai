"""wrongbook draft pipeline

Revision ID: 0012_wrongbook_draft_pipeline
Revises: 0011_goal_recalculation_history
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_wrongbook_draft_pipeline"
down_revision: str | None = "0011_goal_recalculation_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wrongbook_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "wrong_record_id",
            sa.String(length=36),
            sa.ForeignKey("wrong_records.id"),
            nullable=False,
        ),
        sa.Column("ai_job_id", sa.String(length=36), sa.ForeignKey("ai_jobs.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_once", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_wrongbook_drafts_wrong_record_id",
        "wrongbook_drafts",
        ["wrong_record_id"],
    )
    op.create_index("ix_wrongbook_drafts_status", "wrongbook_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_wrongbook_drafts_status", table_name="wrongbook_drafts")
    op.drop_index("ix_wrongbook_drafts_wrong_record_id", table_name="wrongbook_drafts")
    op.drop_table("wrongbook_drafts")
