from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"

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
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hint_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_original: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __mapper_args__ = {"version_id_col": version}


class MasterySnapshot(Base):
    __tablename__ = "mastery_snapshots"

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
    knowledge_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True
    )
    previous_stage: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    recall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    basic_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variant_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transfer_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repeat_error_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_calibration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    transition_reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    computed_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    blocking_reasons_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    remediation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False, default="system")

    __mapper_args__ = {"version_id_col": version}
