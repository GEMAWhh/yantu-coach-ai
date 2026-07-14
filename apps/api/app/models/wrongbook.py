from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    knowledge_node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(40), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)

    __mapper_args__ = {"version_id_col": version}


class QuestionAsset(Base):
    __tablename__ = "question_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), nullable=False)
    asset_role: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    page_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id"), nullable=False, index=True
    )
    wrong_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wrong_records.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attempt_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hint_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __mapper_args__ = {"version_id_col": version}


class WrongRecord(Base):
    __tablename__ = "wrong_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("questions.id"), nullable=False, index=True
    )
    knowledge_node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    surface_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    deep_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisite_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    redo_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_status: Mapped[str] = mapped_column(
        String(60), nullable=False, default="pending_no_hint_redo", index=True
    )
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__ = {"version_id_col": version}


class WrongVerification(Base):
    __tablename__ = "wrong_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    wrong_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wrong_records.id"), nullable=False, unique=True, index=True
    )
    original_redo_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    no_hint_redo_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    variant_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interval_test_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_test_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __mapper_args__ = {"version_id_col": version}


class WrongbookDraft(Base):
    __tablename__ = "wrongbook_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    wrong_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wrong_records.id"), nullable=False, index=True
    )
    ai_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_jobs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    structured_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_errors_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_once: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __mapper_args__ = {"version_id_col": version}
