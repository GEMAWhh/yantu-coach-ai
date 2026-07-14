from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.main import create_app
from app.models.knowledge import KnowledgeEdge, KnowledgeNode
from app.models.mastery import MasteryEvidence, MasterySnapshot
from app.models.planning import Goal, Task, TaskResult
from app.models.wrongbook import Question, WrongRecord
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
    _seed_insights_data(settings)
    yield settings
    get_settings.cache_clear()


def test_graph_endpoints_return_clickable_nodes_and_weak_filter(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        full = client.get("/api/v1/graph/full")
        weak = client.get("/api/v1/graph/weak")

    full_body = full.json()["data"]
    weak_body = weak.json()["data"]
    assert full.status_code == 200
    assert full_body["total_nodes"] == 2
    assert full_body["total_edges"] == 1
    assert {node["id"] for node in full_body["nodes"]} == {
        "knowledge:node-strong",
        "knowledge:node-weak",
    }
    weak_node = next(node for node in full_body["nodes"] if node["object_id"] == "node-weak")
    assert weak_node["object_type"] == "knowledge_node"
    assert weak_node["metrics"]["latest_stage"] == 2
    assert weak_node["metrics"]["evidence_count"] == 1
    assert full_body["edges"][0]["source_id"] == "knowledge:node-strong"
    assert full_body["edges"][0]["target_id"] == "knowledge:node-weak"

    assert weak.status_code == 200
    assert weak_body["total"] == 1
    assert weak_body["items"][0]["object_id"] == "node-weak"
    assert weak_body["items"][0]["blocking_reasons"] == ["needs_variant"]


def test_analytics_endpoints_aggregate_existing_domains(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        overview = client.get("/api/v1/analytics/overview")
        time = client.get("/api/v1/analytics/time")
        errors = client.get("/api/v1/analytics/errors")
        mastery = client.get("/api/v1/analytics/mastery")
        goal_risk = client.get("/api/v1/analytics/goal-risk")

    assert overview.status_code == 200
    overview_data = overview.json()["data"]
    assert overview_data["knowledge_nodes"] == 2
    assert overview_data["goals"] == 2
    assert overview_data["tasks"] == 1
    assert overview_data["task_results"] == 1
    assert overview_data["wrong_records"] == 1
    assert overview_data["average_goal_progress"] == 65
    assert {"key": "completed", "count": 1} in overview_data["task_status"]
    assert {"key": "high", "count": 1} in overview_data["goal_risk"]

    assert time.status_code == 200
    time_data = time.json()["data"]
    assert time_data["estimated_minutes"] == 50
    assert time_data["actual_minutes"] == 70
    assert time_data["by_subject"] == [
        {"subject_id": "math", "estimated_minutes": 50, "actual_minutes": 70}
    ]

    assert errors.status_code == 200
    errors_data = errors.json()["data"]
    assert errors_data["total_wrong_records"] == 1
    assert errors_data["by_status"] == [{"key": "regressed", "count": 1}]
    assert errors_data["by_knowledge_node"] == [{"knowledge_node_id": "node-weak", "count": 1}]

    assert mastery.status_code == 200
    mastery_data = mastery.json()["data"]
    assert mastery_data["latest_snapshot_count"] == 2
    assert mastery_data["weak_node_count"] == 1
    assert {"key": "2", "count": 1} in mastery_data["stage_distribution"]
    assert {"key": "5", "count": 1} in mastery_data["stage_distribution"]

    assert goal_risk.status_code == 200
    risk_data = goal_risk.json()["data"]
    assert risk_data["total_goals"] == 2
    assert {"key": "normal", "count": 1} in risk_data["by_risk_status"]
    assert risk_data["risky_goals"][0]["object_id"] == "goal-risk"


def _seed_insights_data(settings: RuntimeSettings) -> None:
    now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    session_factory = get_session_factory(settings.database_url)
    with session_factory.begin() as session:
        strong = KnowledgeNode(
            id="node-strong",
            subject_id="math",
            code="MATH-001",
            name="函数极限",
            node_type="knowledge",
            importance=80,
            exam_frequency=70,
        )
        weak = KnowledgeNode(
            id="node-weak",
            subject_id="math",
            code="MATH-002",
            name="导数应用",
            node_type="knowledge",
            importance=90,
            exam_frequency=85,
        )
        session.add_all([strong, weak])
        session.flush()
        session.add_all(
            [
                KnowledgeEdge(
                    id="edge-strong-weak",
                    source_node_id=strong.id,
                    target_node_id=weak.id,
                    relation_type="prerequisite",
                    weight=100,
                    source="seed",
                    confirmed=True,
                ),
                MasteryEvidence(
                    id="evidence-weak",
                    knowledge_node_id=weak.id,
                    evidence_type="closed_book_recall",
                    source_type="manual",
                    score=55,
                    sample_count=4,
                    correct_count=2,
                    accuracy=50,
                    occurred_at=now,
                    confirmed=True,
                ),
                MasterySnapshot(
                    id="snapshot-strong",
                    knowledge_node_id=strong.id,
                    previous_stage=4,
                    stage=5,
                    evaluated_at=now,
                    rule_version="mastery-v1.0.0",
                    transition_reason="stable pass",
                    evidence_ids_json=[],
                    computed_metrics_json={},
                    blocking_reasons_json=[],
                ),
                MasterySnapshot(
                    id="snapshot-weak",
                    knowledge_node_id=weak.id,
                    previous_stage=1,
                    stage=2,
                    repeat_error_rate=40,
                    evaluated_at=now,
                    rule_version="mastery-v1.0.0",
                    transition_reason="blocked by variant evidence",
                    evidence_ids_json=["evidence-weak"],
                    computed_metrics_json={"accuracy": 50},
                    blocking_reasons_json=["needs_variant"],
                ),
                Goal(
                    id="goal-risk",
                    level="week",
                    subject_id="math",
                    title="本周导数应用",
                    progress=40,
                    risk_status="high",
                    status="delayed",
                ),
                Goal(
                    id="goal-normal",
                    level="month",
                    subject_id="math",
                    title="本月数学复盘",
                    progress=90,
                    risk_status="normal",
                    status="active",
                ),
                Task(
                    id="task-math",
                    subject_id="math",
                    knowledge_node_id=weak.id,
                    title="导数应用训练",
                    source_type="manual",
                    planned_date=date(2026, 7, 14),
                    estimated_minutes=50,
                    status="completed",
                ),
                Question(
                    id="question-weak",
                    subject_id="math",
                    knowledge_node_id=weak.id,
                    standard_text="求导数应用题。",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                TaskResult(
                    id="task-result-math",
                    task_id="task-math",
                    result_type="partial",
                    completion_ratio=80,
                    actual_minutes=70,
                    confirmed_at=now,
                ),
                WrongRecord(
                    id="wrong-weak",
                    question_id="question-weak",
                    knowledge_node_id=weak.id,
                    current_status="regressed",
                    error_count=2,
                    redo_count=1,
                ),
            ]
        )
