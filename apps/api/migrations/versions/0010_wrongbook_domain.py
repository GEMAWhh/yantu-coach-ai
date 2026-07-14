"""wrongbook domain

Revision ID: 0010_wrongbook_domain
Revises: 0009_evidence_draft_pipeline
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_wrongbook_domain"
down_revision: str | None = "0009_evidence_draft_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSET_ROLES = (
    "'statement','figure','my_answer','marking','standard_answer',"
    "'original_solution','supplement'"
)
ATTEMPT_TYPES = "'original_redo','no_hint_redo','variant','interval_test','transfer_test'"
WRONG_STATUSES = (
    "'pending_analysis','pending_no_hint_redo','pending_variant',"
    "'pending_interval','stable_corrected','regressed'"
)


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=True,
        ),
        sa.Column("standard_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=80), nullable=True),
        sa.Column("difficulty", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("source_year", sa.Integer(), nullable=True),
        sa.Column("source_page", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
    )
    op.create_index("ix_questions_subject_id", "questions", ["subject_id"])
    op.create_index("ix_questions_knowledge_node_id", "questions", ["knowledge_node_id"])
    op.create_index("ix_questions_status", "questions", ["status"])

    op.create_table(
        "question_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "question_id", sa.String(length=36), sa.ForeignKey("questions.id"), nullable=False
        ),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("asset_role", sa.String(length=60), nullable=False),
        sa.Column("page_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(f"asset_role IN ({ASSET_ROLES})", name="ck_question_assets_role"),
        sa.UniqueConstraint(
            "question_id",
            "asset_role",
            "page_order",
            name="uq_question_assets_role_page",
        ),
    )
    op.create_index("ix_question_assets_question_id", "question_assets", ["question_id"])
    op.create_index("ix_question_assets_asset_role", "question_assets", ["asset_role"])

    op.create_table(
        "wrong_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column(
            "question_id", sa.String(length=36), sa.ForeignKey("questions.id"), nullable=False
        ),
        sa.Column(
            "knowledge_node_id",
            sa.String(length=36),
            sa.ForeignKey("knowledge_nodes.id"),
            nullable=True,
        ),
        sa.Column("surface_cause", sa.Text(), nullable=True),
        sa.Column("deep_cause", sa.Text(), nullable=True),
        sa.Column("prerequisite_gap", sa.Text(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("redo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "current_status",
            sa.String(length=60),
            nullable=False,
            server_default="pending_no_hint_redo",
        ),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"current_status IN ({WRONG_STATUSES})", name="ck_wrong_records_status"),
        sa.CheckConstraint("error_count >= 0", name="ck_wrong_records_error_count"),
        sa.CheckConstraint("redo_count >= 0", name="ck_wrong_records_redo_count"),
    )
    op.create_index("ix_wrong_records_question_id", "wrong_records", ["question_id"])
    op.create_index("ix_wrong_records_knowledge_node_id", "wrong_records", ["knowledge_node_id"])
    op.create_index("ix_wrong_records_current_status", "wrong_records", ["current_status"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column(
            "question_id", sa.String(length=36), sa.ForeignKey("questions.id"), nullable=False
        ),
        sa.Column(
            "wrong_record_id",
            sa.String(length=36),
            sa.ForeignKey("wrong_records.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("attempt_type", sa.String(length=60), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("hint_level", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.CheckConstraint(f"attempt_type IN ({ATTEMPT_TYPES})", name="ck_attempts_type"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)", name="ck_attempts_score"
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_attempts_duration",
        ),
        sa.CheckConstraint("hint_level IS NULL OR hint_level >= 0", name="ck_attempts_hint"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_attempts_confidence",
        ),
        sa.UniqueConstraint(
            "wrong_record_id",
            "idempotency_key",
            name="uq_attempts_wrong_record_idempotency",
        ),
    )
    op.create_index("ix_attempts_question_id", "attempts", ["question_id"])
    op.create_index("ix_attempts_wrong_record_id", "attempts", ["wrong_record_id"])
    op.create_index("ix_attempts_attempt_type", "attempts", ["attempt_type"])

    op.create_table(
        "wrong_verifications",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "wrong_record_id",
            sa.String(length=36),
            sa.ForeignKey("wrong_records.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("original_redo_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("no_hint_redo_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("variant_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interval_test_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transfer_test_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_attempt_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_wrong_verifications_wrong_record_id",
        "wrong_verifications",
        ["wrong_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wrong_verifications_wrong_record_id", table_name="wrong_verifications")
    op.drop_table("wrong_verifications")
    op.drop_index("ix_attempts_attempt_type", table_name="attempts")
    op.drop_index("ix_attempts_wrong_record_id", table_name="attempts")
    op.drop_index("ix_attempts_question_id", table_name="attempts")
    op.drop_table("attempts")
    op.drop_index("ix_wrong_records_current_status", table_name="wrong_records")
    op.drop_index("ix_wrong_records_knowledge_node_id", table_name="wrong_records")
    op.drop_index("ix_wrong_records_question_id", table_name="wrong_records")
    op.drop_table("wrong_records")
    op.drop_index("ix_question_assets_asset_role", table_name="question_assets")
    op.drop_index("ix_question_assets_question_id", table_name="question_assets")
    op.drop_table("question_assets")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_index("ix_questions_knowledge_node_id", table_name="questions")
    op.drop_index("ix_questions_subject_id", table_name="questions")
    op.drop_table("questions")
