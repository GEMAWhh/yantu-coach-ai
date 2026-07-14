from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    job_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__ = {"version_id_col": version}


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    study_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    asset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_facts_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    inferences_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    uncertain_fields_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    teaching_judgment_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    suggested_actions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __mapper_args__ = {"version_id_col": version}


class EvidenceAsset(Base):
    __tablename__ = "evidence_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    evidence_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_records.id"), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), nullable=False)
    page_order: Mapped[int] = mapped_column(Integer, nullable=False)


class EvidenceDraft(Base):
    __tablename__ = "evidence_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    evidence_record_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_records.id"), nullable=False, index=True
    )
    ai_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_jobs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    structured_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_errors_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_once: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __mapper_args__ = {"version_id_col": version}
