from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

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
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    importance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_frequency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active", index=True)

    __mapper_args__ = {"version_id_col": version}


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="uq_knowledge_edges_relation",
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
    created_by: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="user")
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __mapper_args__ = {"version_id_col": version}
