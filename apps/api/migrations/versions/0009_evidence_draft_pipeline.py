"""evidence draft pipeline

Revision ID: 0009_evidence_draft_pipeline
Revises: 0008_time_calibration
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_evidence_draft_pipeline"
down_revision: str | None = "0008_time_calibration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_jobs_job_type", "ai_jobs", ["job_type"])
    op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"])

    op.create_table(
        "evidence_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("asset_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmed_facts_json", sa.JSON(), nullable=True),
        sa.Column("inferences_json", sa.JSON(), nullable=True),
        sa.Column("uncertain_fields_json", sa.JSON(), nullable=True),
        sa.Column("teaching_judgment_json", sa.JSON(), nullable=True),
        sa.Column("suggested_actions_json", sa.JSON(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evidence_records_study_date", "evidence_records", ["study_date"])
    op.create_index("ix_evidence_records_subject_id", "evidence_records", ["subject_id"])
    op.create_index("ix_evidence_records_status", "evidence_records", ["status"])

    op.create_table(
        "evidence_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "evidence_record_id",
            sa.String(length=36),
            sa.ForeignKey("evidence_records.id"),
            nullable=False,
        ),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("page_order", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_evidence_assets_evidence_record_id", "evidence_assets", ["evidence_record_id"]
    )

    op.create_table(
        "evidence_drafts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "evidence_record_id",
            sa.String(length=36),
            sa.ForeignKey("evidence_records.id"),
            nullable=False,
        ),
        sa.Column("ai_job_id", sa.String(length=36), sa.ForeignKey("ai_jobs.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("structured_json", sa.JSON(), nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("confirmed_once", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_evidence_drafts_evidence_record_id", "evidence_drafts", ["evidence_record_id"]
    )
    op.create_index("ix_evidence_drafts_status", "evidence_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_evidence_drafts_status", table_name="evidence_drafts")
    op.drop_index("ix_evidence_drafts_evidence_record_id", table_name="evidence_drafts")
    op.drop_table("evidence_drafts")
    op.drop_index("ix_evidence_assets_evidence_record_id", table_name="evidence_assets")
    op.drop_table("evidence_assets")
    op.drop_index("ix_evidence_records_status", table_name="evidence_records")
    op.drop_index("ix_evidence_records_subject_id", table_name="evidence_records")
    op.drop_index("ix_evidence_records_study_date", table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_index("ix_ai_jobs_status", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_job_type", table_name="ai_jobs")
    op.drop_table("ai_jobs")
