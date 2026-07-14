from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.service import KnowledgeTreeNode, PrerequisiteCheck
from app.models.knowledge import KnowledgeEdge, KnowledgeNode

NodeType = Literal["subject", "module", "chapter", "knowledge"]
RelationType = Literal[
    "belongs_to",
    "prerequisite",
    "similar_to",
    "confused_with",
    "co_tested",
    "transforms_to",
]


class KnowledgeNodeCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    node_type: NodeType
    parent_id: str | None = None
    subject_id: str | None = None
    importance: int | None = Field(default=None, ge=0, le=100)
    exam_frequency: int | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    status: str = Field(default="active", min_length=1, max_length=40)


class KnowledgeNodeUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    importance: int | None = Field(default=None, ge=0, le=100)
    exam_frequency: int | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=40)


class KnowledgeNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    is_deleted: bool
    deleted_at: datetime | None
    subject_id: str
    parent_id: str | None
    code: str
    name: str
    node_type: NodeType
    importance: int | None
    exam_frequency: int | None
    description: str | None
    status: str

    @classmethod
    def from_model(cls, node: KnowledgeNode) -> KnowledgeNodeResponse:
        return cls(
            id=node.id,
            version=node.version,
            created_at=node.created_at,
            updated_at=node.updated_at,
            created_by=node.created_by,
            is_deleted=node.is_deleted,
            deleted_at=node.deleted_at,
            subject_id=node.subject_id or node.id,
            parent_id=node.parent_id,
            code=node.code,
            name=node.name,
            node_type=cast(NodeType, node.node_type),
            importance=node.importance,
            exam_frequency=node.exam_frequency,
            description=node.description,
            status=node.status,
        )


class KnowledgeNodeListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[KnowledgeNodeResponse]
    total: int


class KnowledgeNodeTreeResponse(KnowledgeNodeResponse):
    children: list[KnowledgeNodeTreeResponse] = Field(default_factory=list)

    @classmethod
    def from_tree(cls, tree: KnowledgeTreeNode) -> KnowledgeNodeTreeResponse:
        node = tree.node
        return cls(
            id=node.id,
            version=node.version,
            created_at=node.created_at,
            updated_at=node.updated_at,
            created_by=node.created_by,
            is_deleted=node.is_deleted,
            deleted_at=node.deleted_at,
            subject_id=node.subject_id or node.id,
            parent_id=node.parent_id,
            code=node.code,
            name=node.name,
            node_type=cast(NodeType, node.node_type),
            importance=node.importance,
            exam_frequency=node.exam_frequency,
            description=node.description,
            status=node.status,
            children=[cls.from_tree(child) for child in tree.children],
        )


class KnowledgeEdgeCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    weight: int = Field(default=100, ge=0, le=100)
    source: str = Field(default="user", min_length=1, max_length=80)
    confirmed: bool = True


class KnowledgeEdgeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    source_node_id: str
    target_node_id: str
    relation_type: RelationType
    weight: int
    source: str
    confirmed: bool
    is_deleted: bool
    deleted_at: datetime | None

    @classmethod
    def from_model(cls, edge: KnowledgeEdge) -> KnowledgeEdgeResponse:
        return cls(
            id=edge.id,
            version=edge.version,
            created_at=edge.created_at,
            updated_at=edge.updated_at,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            relation_type=cast(RelationType, edge.relation_type),
            weight=edge.weight,
            source=edge.source,
            confirmed=edge.confirmed,
            is_deleted=edge.is_deleted,
            deleted_at=edge.deleted_at,
        )


class PrerequisiteBlockerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    relation_id: str
    prerequisite_node_id: str
    prerequisite_code: str
    prerequisite_name: str
    status: str
    reason: Literal["PREREQUISITE_NOT_MET"]


class PrerequisiteCheckResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    satisfied: bool
    blocking_reasons: list[PrerequisiteBlockerResponse]

    @classmethod
    def from_check(cls, check: PrerequisiteCheck) -> PrerequisiteCheckResponse:
        return cls(
            node_id=check.node_id,
            satisfied=check.satisfied,
            blocking_reasons=[
                PrerequisiteBlockerResponse(
                    relation_id=blocker.relation_id,
                    prerequisite_node_id=blocker.prerequisite_node_id,
                    prerequisite_code=blocker.prerequisite_code,
                    prerequisite_name=blocker.prerequisite_name,
                    status=blocker.status,
                    reason="PREREQUISITE_NOT_MET",
                )
                for blocker in check.blocking_reasons
            ],
        )
