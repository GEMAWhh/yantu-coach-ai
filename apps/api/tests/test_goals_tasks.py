from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.planning.service as planning_module
from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.knowledge.service import create_knowledge_node
from app.main import create_app
from app.models.mastery import MasterySnapshot
from app.models.planning import Goal, TaskResult
from app.planning.service import (
    create_goal,
    create_task,
    get_goal,
    set_task_status,
    submit_task_result,
)
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


def _create_knowledge(session: Session) -> str:
    subject = create_knowledge_node(session, code="gt.math", name="Math", node_type="subject")
    module = create_knowledge_node(
        session,
        code="gt.math.module",
        name="Module",
        node_type="module",
        parent_id=subject.id,
    )
    chapter = create_knowledge_node(
        session,
        code="gt.math.module.chapter",
        name="Chapter",
        node_type="chapter",
        parent_id=module.id,
    )
    node = create_knowledge_node(
        session,
        code="gt.math.module.chapter.node",
        name="Node",
        node_type="knowledge",
        parent_id=chapter.id,
    )
    return node.id


def test_week_goal_task_result_progress_and_source_traceability(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    planned_date = date(2026, 7, 14)
    with session_factory.begin() as session:
        goal = create_goal(
            session,
            level="week",
            title="Finish closed-loop practice",
            estimated_minutes=100,
            completion_standard="Submit real results",
        )
        task = create_task(
            session,
            title="Closed-book recall",
            planned_date=planned_date,
            estimated_minutes=50,
            source_type="goal",
            source_id=goal.id,
            goal_id=goal.id,
            reason="Weekly goal requires active recall evidence",
        )
        submitted = submit_task_result(
            session,
            task.id,
            result_type="partial",
            completion_ratio=80,
            actual_minutes=45,
            question_count=5,
            correct_count=4,
            accuracy=80,
            confidence=70,
            problem_description="One condition was missed",
            confirmed_at=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
            idempotency_key="result-1",
        )
        refreshed_goal = get_goal(session, goal.id)

    assert task.source_type == "goal"
    assert task.source_id == goal.id
    assert task.reason == "Weekly goal requires active recall evidence"
    assert task.status == "pending"
    assert submitted.created is True
    assert submitted.result.actual_minutes == 45
    assert submitted.result.accuracy == 80
    assert submitted.result.confidence == 70
    assert submitted.result.problem_description == "One condition was missed"
    assert refreshed_goal.actual_minutes == 45
    assert refreshed_goal.progress == 80


def test_task_result_submission_is_idempotent(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        goal = create_goal(session, level="week", title="Weekly goal")
        task = create_task(
            session,
            title="Basic practice",
            planned_date=date(2026, 7, 14),
            estimated_minutes=30,
            source_type="goal",
            source_id=goal.id,
            goal_id=goal.id,
        )
        first = submit_task_result(
            session,
            task.id,
            result_type="completed",
            completion_ratio=100,
            actual_minutes=30,
            idempotency_key="same-key",
        )
        second = submit_task_result(
            session,
            task.id,
            result_type="completed",
            completion_ratio=100,
            actual_minutes=30,
            idempotency_key="same-key",
        )
        count = session.scalar(select(func.count(TaskResult.id)))

    assert first.created is True
    assert second.created is False
    assert second.result.id == first.result.id
    assert count == 1


def test_task_result_rollback_removes_partial_write(
    test_settings: RuntimeSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("audit failed")

    with session_factory.begin() as session:
        goal = create_goal(session, level="week", title="Rollback goal")
        task = create_task(
            session,
            title="Rollback task",
            planned_date=date(2026, 7, 14),
            estimated_minutes=20,
            source_type="goal",
            source_id=goal.id,
            goal_id=goal.id,
        )
        task_id = task.id
        goal_id = goal.id

    monkeypatch.setattr(planning_module, "write_audit_event", fail_audit)
    with pytest.raises(RuntimeError, match="audit failed"):
        with session_factory.begin() as session:
            submit_task_result(
                session,
                task_id,
                result_type="completed",
                completion_ratio=100,
                actual_minutes=20,
            )

    with session_factory() as session:
        result_count = session.scalar(select(func.count(TaskResult.id)))
        stored_goal = session.get(Goal, goal_id)

    assert result_count == 0
    assert stored_goal is not None
    assert stored_goal.progress == 0
    assert stored_goal.actual_minutes == 0


def test_task_completion_and_results_do_not_change_mastery_stage(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        knowledge_node_id = _create_knowledge(session)
        goal = create_goal(session, level="week", title="No mastery shortcut")
        task = create_task(
            session,
            title="Practice without mastery shortcut",
            planned_date=date(2026, 7, 14),
            estimated_minutes=25,
            source_type="knowledge_node",
            source_id=knowledge_node_id,
            goal_id=goal.id,
            knowledge_node_id=knowledge_node_id,
        )
        submit_task_result(
            session,
            task.id,
            result_type="completed",
            completion_ratio=100,
            actual_minutes=25,
            accuracy=100,
        )
        set_task_status(session, task.id, status="completed")
        snapshot_count = session.scalar(select(func.count(MasterySnapshot.id)))

    assert snapshot_count == 0


def test_planning_api_version_conflict_and_today_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        goal_response = client.post(
            "/api/v1/goals",
            json={
                "level": "week",
                "title": "API weekly goal",
                "estimated_minutes": 90,
                "completion_standard": "Store real task results",
            },
            headers={"X-Request-ID": "goal-create"},
        )
        goal = goal_response.json()["data"]
        task_response = client.post(
            "/api/v1/tasks",
            json={
                "goal_id": goal["id"],
                "title": "API task",
                "planned_date": "2026-07-14",
                "estimated_minutes": 30,
                "source_type": "goal",
                "source_id": goal["id"],
                "reason": "Trace source from weekly goal",
            },
            headers={"X-Request-ID": "task-create"},
        )
        task = task_response.json()["data"]
        today_response = client.get("/api/v1/today?date=2026-07-14")
        first_result = client.post(
            f"/api/v1/tasks/{task['id']}/results",
            json={
                "result_type": "completed",
                "completion_ratio": 100,
                "actual_minutes": 32,
                "question_count": 4,
                "correct_count": 3,
                "accuracy": 75,
                "confidence": 65,
                "problem_description": "Needs one follow-up",
            },
            headers={"Idempotency-Key": "api-result", "X-Request-ID": "task-result"},
        )
        second_result = client.post(
            f"/api/v1/tasks/{task['id']}/results",
            json={
                "result_type": "completed",
                "completion_ratio": 100,
                "actual_minutes": 32,
            },
            headers={"Idempotency-Key": "api-result"},
        )
        refreshed_goal = client.get(f"/api/v1/goals/{goal['id']}")
        conflict = client.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "stale update"},
            headers={"If-Match": "999", "X-Request-ID": "stale-task"},
        )

    assert goal_response.status_code == 200
    assert goal_response.json()["meta"] == {"request_id": "goal-create"}
    assert task_response.status_code == 200
    assert task["status"] == "pending"
    assert task["source_type"] == "goal"
    assert task["source_id"] == goal["id"]
    assert today_response.status_code == 200
    assert today_response.json()["data"]["total_tasks"] == 1
    assert today_response.json()["data"]["tasks"][0]["reason"] == "Trace source from weekly goal"
    assert first_result.status_code == 200
    assert first_result.json()["data"]["created"] is True
    assert first_result.json()["data"]["result"]["actual_minutes"] == 32
    assert second_result.status_code == 200
    assert second_result.json()["data"]["created"] is False
    assert (
        second_result.json()["data"]["result"]["id"] == first_result.json()["data"]["result"]["id"]
    )
    assert refreshed_goal.json()["data"]["progress"] == 100
    assert refreshed_goal.json()["data"]["actual_minutes"] == 32
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "VERSION_CONFLICT"
    assert conflict.json()["error"]["request_id"] == "stale-task"

    get_settings.cache_clear()
