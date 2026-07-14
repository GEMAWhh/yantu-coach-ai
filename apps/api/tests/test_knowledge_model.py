from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.knowledge.service import (
    KnowledgeError,
    check_prerequisites,
    create_knowledge_edge,
    create_knowledge_node,
    get_knowledge_tree,
    list_knowledge_nodes,
    soft_delete_knowledge_node,
    update_knowledge_node,
)
from app.main import create_app
from app.models.knowledge import KnowledgeEdge, KnowledgeNode
from app.settings import RuntimeSettings, get_settings


@pytest.fixture
def test_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[RuntimeSettings, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    settings = get_settings()
    initialize_database(settings)
    yield settings
    get_settings.cache_clear()


def _create_math_chain(
    session: Session,
) -> tuple[KnowledgeNode, KnowledgeNode, KnowledgeNode, KnowledgeNode]:
    subject = create_knowledge_node(
        session,
        code="math",
        name="Math",
        node_type="subject",
        status="satisfied",
    )
    module = create_knowledge_node(
        session,
        code="math.calculus",
        name="Calculus",
        node_type="module",
        parent_id=subject.id,
    )
    chapter = create_knowledge_node(
        session,
        code="math.calculus.derivative",
        name="Derivative",
        node_type="chapter",
        parent_id=module.id,
    )
    knowledge = create_knowledge_node(
        session,
        code="math.calculus.derivative.extreme",
        name="Extreme value",
        node_type="knowledge",
        parent_id=chapter.id,
    )
    session.flush()
    return subject, module, chapter, knowledge


def test_recursive_hierarchy_query(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        subject, module, chapter, knowledge = _create_math_chain(session)
        tree = get_knowledge_tree(session, subject.id)

    assert tree.node.id == subject.id
    assert tree.children[0].node.id == module.id
    assert tree.children[0].children[0].node.id == chapter.id
    assert tree.children[0].children[0].children[0].node.id == knowledge.id


def test_prerequisite_check_reports_blockers_and_satisfied(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        _, _, _, target = _create_math_chain(session)
        prerequisite = create_knowledge_node(
            session,
            code="math.calculus.derivative.limit",
            name="Limit prerequisite",
            node_type="knowledge",
            parent_id=target.parent_id,
            status="active",
        )
        session.flush()
        create_knowledge_edge(
            session,
            source_node_id=prerequisite.id,
            target_node_id=target.id,
            relation_type="prerequisite",
        )
        blocked = check_prerequisites(session, target.id)
        update_knowledge_node(session, prerequisite.id, status="satisfied")
        satisfied = check_prerequisites(session, target.id)

    assert blocked.satisfied is False
    assert blocked.blocking_reasons[0].reason == "PREREQUISITE_NOT_MET"
    assert blocked.blocking_reasons[0].prerequisite_node_id == prerequisite.id
    assert satisfied.satisfied is True
    assert satisfied.blocking_reasons == []


def test_prerequisite_cycle_is_rejected(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        _, _, chapter, _ = _create_math_chain(session)
        first = create_knowledge_node(
            session,
            code="math.calculus.derivative.a",
            name="A",
            node_type="knowledge",
            parent_id=chapter.id,
        )
        second = create_knowledge_node(
            session,
            code="math.calculus.derivative.b",
            name="B",
            node_type="knowledge",
            parent_id=chapter.id,
        )
        session.flush()
        create_knowledge_edge(
            session,
            source_node_id=first.id,
            target_node_id=second.id,
            relation_type="prerequisite",
        )
        with pytest.raises(KnowledgeError, match="cycle"):
            create_knowledge_edge(
                session,
                source_node_id=second.id,
                target_node_id=first.id,
                relation_type="prerequisite",
            )


def test_soft_delete_hides_subtree_and_related_edges(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        _, _, _, target = _create_math_chain(session)
        prerequisite = create_knowledge_node(
            session,
            code="math.calculus.derivative.limit",
            name="Limit prerequisite",
            node_type="knowledge",
            parent_id=target.parent_id,
            status="active",
        )
        session.flush()
        edge = create_knowledge_edge(
            session,
            source_node_id=prerequisite.id,
            target_node_id=target.id,
            relation_type="prerequisite",
        )
        soft_delete_knowledge_node(session, prerequisite.id)
        visible_nodes = list_knowledge_nodes(session)
        check = check_prerequisites(session, target.id)
        session.flush()
        stored_edge = session.get(KnowledgeEdge, edge.id)

    assert prerequisite.id not in {node.id for node in visible_nodes}
    assert check.satisfied is True
    assert stored_edge is not None
    assert stored_edge.is_deleted is True


def test_api_creates_tree_and_reports_prerequisite_blocker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        subject = client.post(
            "/api/v1/knowledge/nodes",
            json={"code": "math", "name": "Math", "node_type": "subject"},
            headers={"X-Request-ID": "knowledge-subject"},
        )
        subject_id = subject.json()["data"]["id"]
        module = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "math.calculus",
                "name": "Calculus",
                "node_type": "module",
                "parent_id": subject_id,
            },
        )
        module_id = module.json()["data"]["id"]
        chapter = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "math.calculus.derivative",
                "name": "Derivative",
                "node_type": "chapter",
                "parent_id": module_id,
            },
        )
        chapter_id = chapter.json()["data"]["id"]
        target = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "math.calculus.derivative.extreme",
                "name": "Extreme value",
                "node_type": "knowledge",
                "parent_id": chapter_id,
            },
        )
        prereq = client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "math.calculus.derivative.limit",
                "name": "Limit prerequisite",
                "node_type": "knowledge",
                "parent_id": chapter_id,
            },
        )
        edge = client.post(
            "/api/v1/knowledge/edges",
            json={
                "source_node_id": prereq.json()["data"]["id"],
                "target_node_id": target.json()["data"]["id"],
                "relation_type": "prerequisite",
            },
        )
        tree = client.get(f"/api/v1/knowledge/nodes/{subject_id}/tree")
        prerequisites = client.get(
            f"/api/v1/knowledge/nodes/{target.json()['data']['id']}/prerequisites"
        )
        invalid = client.post(
            "/api/v1/knowledge/nodes",
            json={"code": "bad", "name": "Bad", "node_type": "chapter"},
            headers={"X-Request-ID": "knowledge-invalid"},
        )

    assert subject.status_code == 200
    assert subject.json()["meta"] == {"request_id": "knowledge-subject"}
    assert module.status_code == 200
    assert chapter.status_code == 200
    assert target.status_code == 200
    assert prereq.status_code == 200
    assert edge.status_code == 200
    assert tree.status_code == 200
    assert tree.json()["data"]["children"][0]["children"][0]["id"] == chapter_id
    assert prerequisites.status_code == 200
    assert prerequisites.json()["data"]["satisfied"] is False
    assert prerequisites.json()["data"]["blocking_reasons"][0]["reason"] == "PREREQUISITE_NOT_MET"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "KNOWLEDGE_PARENT_REQUIRED"
    assert invalid.json()["error"]["request_id"] == "knowledge-invalid"

    get_settings.cache_clear()


def test_database_persists_nodes_and_edges(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        _, _, _, target = _create_math_chain(session)
        node_count = session.scalar(select(func.count(KnowledgeNode.id)))
        edge_count = session.scalar(select(func.count(KnowledgeEdge.id)))

    assert target.subject_id is not None
    assert node_count == 4
    assert edge_count == 0
