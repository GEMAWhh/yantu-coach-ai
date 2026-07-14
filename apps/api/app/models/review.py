from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ReviewSchedule(Base):
    __tablename__ = "review_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    knowledge_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True
    )
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    current_stage: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_result_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_snapshot_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("mastery_snapshots.id"), nullable=True
    )
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    next_reason: Mapped[str] = mapped_column(Text, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class ReviewResult(Base):
    __tablename__ = "review_results"
    __table_args__ = (
        UniqueConstraint("schedule_id", "idempotency_key", name="uq_review_results_idempotency"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    schedule_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_schedules.id"), nullable=False, index=True
    )
    knowledge_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result_type: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    independent_timepoint: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    evidence_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("mastery_evidence.id"), nullable=True
    )
    snapshot_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("mastery_snapshots.id"), nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __mapper_args__ = {"version_id_col": version}
