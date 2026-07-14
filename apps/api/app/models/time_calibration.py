from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class TimeCoefficient(Base):
    __tablename__ = "time_coefficients"
    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "task_type",
            "difficulty",
            name="uq_time_coefficients_scope",
        ),
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
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    coefficient: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overtime_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_task_result_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("task_results.id"), nullable=True
    )
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    rationale_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __mapper_args__ = {"version_id_col": version}


class TimeAdjustment(Base):
    __tablename__ = "time_adjustments"
    __table_args__ = (UniqueConstraint("task_result_id", name="uq_time_adjustments_task_result"),)

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
    coefficient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("time_coefficients.id"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    task_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_results.id"), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    applied_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    new_coefficient: Mapped[float] = mapped_column(Float, nullable=False)
    ignored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ignore_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    overtime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    suggested_split: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __mapper_args__ = {"version_id_col": version}
