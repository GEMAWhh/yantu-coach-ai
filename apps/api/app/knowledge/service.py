from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.base import utc_now
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

NODE_TYPE_ORDER: dict[str, int] = {
    "subject": 0,
    "module": 1,
    "chapter": 2,
    "knowledge": 3,
}
RELATION_TYPES = {
    "belongs_to",
    "prerequisite",
    "similar_to",
    "confused_with",
    "co_tested",
    "transforms_to",
}
SATISFIED_NODE_STATUSES = {"satisfied", "mastered", "completed"}


class KnowledgeError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "KNOWLEDGE_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class KnowledgeTreeNode:
    node: KnowledgeNode
    children: list["KnowledgeTreeNode"] = field(default_factory=list)


@dataclass(frozen=True)
class PrerequisiteBlocker:
    relation_id: str
    prerequisite_node_id: str
    prerequisite_code: str
    prerequisite_name: str
    status: str
    reason: str


@dataclass(frozen=True)
class PrerequisiteCheck:
    node_id: str
    satisfied: bool
    blocking_reasons: list[PrerequisiteBlocker]


def create_knowledge_node(
    session: Session,
    *,
    code: str,
    name: str,
    node_type: NodeType,
    parent_id: str | None = None,
    subject_id: str | None = None,
    importance: int | None = None,
    exam_frequency: int | None = None,
    description: str | None = None,
    status: str = "active",
    created_by: str = "system",
) -> KnowledgeNode:
    parent = _get_parent_for_create(session, parent_id)
    _validate_node_type(node_type)
    _validate_hierarchy(parent, node_type)
    node_id = str(uuid4())
    resolved_subject_id = _resolve_subject_id(
        node_id=node_id,
        node_type=node_type,
        parent=parent,
        subject_id=subject_id,
    )
    node = KnowledgeNode(
        id=node_id,
        code=code,
        name=name,
        node_type=node_type,
        parent_id=parent_id,
        subject_id=resolved_subject_id,
        importance=importance,
        exam_frequency=exam_frequency,
        description=description,
        status=status,
        created_by=created_by,
    )
    session.add(node)
    session.flush()
    return node


def update_knowledge_node(
    session: Session,
    node_id: str,
    *,
    name: str | None = None,
    importance: int | None = None,
    exam_frequency: int | None = None,
    description: str | None = None,
    status: str | None = None,
) -> KnowledgeNode:
    node = get_knowledge_node(session, node_id)
    if name is not None:
        node.name = name
    if importance is not None:
        node.importance = importance
    if exam_frequency is not None:
        node.exam_frequency = exam_frequency
    if description is not None:
        node.description = description
    if status is not None:
        node.status = status
    session.flush()
    return node


def get_knowledge_node(
    session: Session,
    node_id: str,
    *,
    include_deleted: bool = False,
) -> KnowledgeNode:
    node = session.get(KnowledgeNode, node_id)
    if node is None or (node.is_deleted and not include_deleted):
        raise KnowledgeError(
            "knowledge node not found",
            code="KNOWLEDGE_NODE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"node_id": node_id},
        )
    return node


def list_knowledge_nodes(
    session: Session,
    *,
    parent_id: str | None = None,
    include_deleted: bool = False,
) -> list[KnowledgeNode]:
    statement = select(KnowledgeNode)
    if parent_id is not None:
        statement = statement.where(KnowledgeNode.parent_id == parent_id)
    if not include_deleted:
        statement = statement.where(KnowledgeNode.is_deleted.is_(False))
    statement = statement.order_by(KnowledgeNode.code)
    return list(session.scalars(statement).all())


def get_knowledge_tree(session: Session, root_node_id: str) -> KnowledgeTreeNode:
    root = get_knowledge_node(session, root_node_id)
    nodes = list_knowledge_nodes(session)
    children_by_parent: dict[str | None, list[KnowledgeNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    def build(node: KnowledgeNode) -> KnowledgeTreeNode:
        children = [build(child) for child in children_by_parent.get(node.id, [])]
        return KnowledgeTreeNode(node=node, children=children)

    return build(root)


def create_knowledge_edge(
    session: Session,
    *,
    source_node_id: str,
    target_node_id: str,
    relation_type: RelationType,
    weight: int = 100,
    source: str = "user",
    confirmed: bool = True,
    created_by: str = "system",
) -> KnowledgeEdge:
    if source_node_id == target_node_id:
        raise KnowledgeError(
            "knowledge edge cannot point to itself",
            code="KNOWLEDGE_EDGE_SELF_REFERENCE",
            status_code=HTTPStatus.CONFLICT,
            details={"node_id": source_node_id},
        )
    _validate_relation_type(relation_type)
    source_node = get_knowledge_node(session, source_node_id)
    target_node = get_knowledge_node(session, target_node_id)
    if relation_type == "prerequisite" and _has_prerequisite_path(
        session,
        start_node_id=target_node.id,
        target_node_id=source_node.id,
    ):
        raise KnowledgeError(
            "prerequisite edge would create a cycle",
            code="KNOWLEDGE_PREREQUISITE_CYCLE",
            status_code=HTTPStatus.CONFLICT,
            details={"source_node_id": source_node_id, "target_node_id": target_node_id},
        )
    edge = KnowledgeEdge(
        id=str(uuid4()),
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        relation_type=relation_type,
        weight=weight,
        source=source,
        confirmed=confirmed,
        created_by=created_by,
    )
    session.add(edge)
    session.flush()
    return edge


def check_prerequisites(session: Session, node_id: str) -> PrerequisiteCheck:
    node = get_knowledge_node(session, node_id)
    rows = session.execute(
        select(KnowledgeEdge, KnowledgeNode)
        .join(KnowledgeNode, KnowledgeEdge.source_node_id == KnowledgeNode.id)
        .where(
            KnowledgeEdge.target_node_id == node.id,
            KnowledgeEdge.relation_type == "prerequisite",
            KnowledgeEdge.is_deleted.is_(False),
            KnowledgeNode.is_deleted.is_(False),
        )
        .order_by(KnowledgeNode.code)
    ).all()
    blockers = [
        PrerequisiteBlocker(
            relation_id=edge.id,
            prerequisite_node_id=prerequisite.id,
            prerequisite_code=prerequisite.code,
            prerequisite_name=prerequisite.name,
            status=prerequisite.status,
            reason="PREREQUISITE_NOT_MET",
        )
        for edge, prerequisite in rows
        if prerequisite.status not in SATISFIED_NODE_STATUSES
    ]
    return PrerequisiteCheck(
        node_id=node.id,
        satisfied=not blockers,
        blocking_reasons=blockers,
    )


def soft_delete_knowledge_node(session: Session, node_id: str) -> KnowledgeNode:
    node = get_knowledge_node(session, node_id)
    deleted_at = utc_now()
    node_ids = _collect_descendant_ids(session, node.id)
    nodes = session.scalars(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))).all()
    for item in nodes:
        item.is_deleted = True
        item.deleted_at = deleted_at
        item.status = "archived"
    edges = session.scalars(
        select(KnowledgeEdge).where(
            or_(
                KnowledgeEdge.source_node_id.in_(node_ids),
                KnowledgeEdge.target_node_id.in_(node_ids),
            ),
            KnowledgeEdge.is_deleted.is_(False),
        )
    ).all()
    for edge in edges:
        edge.is_deleted = True
        edge.deleted_at = deleted_at
    session.flush()
    return node


def _get_parent_for_create(session: Session, parent_id: str | None) -> KnowledgeNode | None:
    if parent_id is None:
        return None
    return get_knowledge_node(session, parent_id)


def _validate_node_type(node_type: str) -> None:
    if node_type not in NODE_TYPE_ORDER:
        raise KnowledgeError(
            "unsupported knowledge node type",
            code="KNOWLEDGE_NODE_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"node_type": node_type},
        )


def _validate_relation_type(relation_type: str) -> None:
    if relation_type not in RELATION_TYPES:
        raise KnowledgeError(
            "unsupported knowledge edge relation type",
            code="KNOWLEDGE_RELATION_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"relation_type": relation_type},
        )


def _validate_hierarchy(parent: KnowledgeNode | None, node_type: str) -> None:
    if parent is None:
        if node_type != "subject":
            raise KnowledgeError(
                "non-subject knowledge node requires a parent",
                code="KNOWLEDGE_PARENT_REQUIRED",
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                details={"node_type": node_type},
            )
        return
    expected_parent_order = NODE_TYPE_ORDER[node_type] - 1
    if NODE_TYPE_ORDER[parent.node_type] != expected_parent_order:
        raise KnowledgeError(
            "knowledge node hierarchy must follow subject -> module -> chapter -> knowledge",
            code="KNOWLEDGE_HIERARCHY_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"parent_type": parent.node_type, "node_type": node_type},
        )


def _resolve_subject_id(
    *,
    node_id: str,
    node_type: str,
    parent: KnowledgeNode | None,
    subject_id: str | None,
) -> str:
    if subject_id is not None:
        return subject_id
    if node_type == "subject":
        return node_id
    if parent is None:
        return node_id
    return parent.subject_id or parent.id


def _has_prerequisite_path(
    session: Session,
    *,
    start_node_id: str,
    target_node_id: str,
) -> bool:
    adjacency = _active_prerequisite_adjacency(session)
    visited: set[str] = set()
    stack = [start_node_id]
    while stack:
        current = stack.pop()
        if current == target_node_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adjacency.get(current, []))
    return False


def _active_prerequisite_adjacency(session: Session) -> dict[str, list[str]]:
    edges = session.scalars(
        select(KnowledgeEdge).where(
            KnowledgeEdge.relation_type == "prerequisite",
            KnowledgeEdge.is_deleted.is_(False),
        )
    ).all()
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge.target_node_id)
    return adjacency


def _collect_descendant_ids(session: Session, root_node_id: str) -> list[str]:
    children_by_parent: dict[str | None, list[str]] = {}
    rows = session.scalars(select(KnowledgeNode).where(KnowledgeNode.is_deleted.is_(False))).all()
    for node in rows:
        children_by_parent.setdefault(node.parent_id, []).append(node.id)
    collected: list[str] = []
    stack = [root_node_id]
    while stack:
        current = stack.pop()
        if current in collected:
            continue
        collected.append(current)
        stack.extend(children_by_parent.get(current, []))
    return collected
