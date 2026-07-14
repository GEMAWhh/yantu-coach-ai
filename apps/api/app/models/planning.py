from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class Goal(Base):
    __tablename__ = "goals"

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
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    level: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_status: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)
    adjustment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __mapper_args__ = {"version_id_col": version}


class Task(Base):
    __tablename__ = "tasks"

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
    goal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("goals.id"), nullable=True, index=True
    )
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    knowledge_node_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    wrong_record_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_schedule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False, default="study")
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    planned_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cognitive_load: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisite_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)

    __mapper_args__ = {"version_id_col": version}


class TaskResult(Base):
    __tablename__ = "task_results"
    __table_args__ = (
        UniqueConstraint("task_id", "idempotency_key", name="uq_task_results_idempotency"),
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
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    result_type: Mapped[str] = mapped_column(String(40), nullable=False)
    completion_ratio: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hint_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    focus_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __mapper_args__ = {"version_id_col": version}
