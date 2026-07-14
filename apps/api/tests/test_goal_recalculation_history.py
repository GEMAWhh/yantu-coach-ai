from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.main import create_app
from app.models.planning import GoalHistoryEvent
from app.planning.service import create_goal, create_task, submit_task_result
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


def test_task_result_recalculates_parent_goal_and_records_history(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        parent = create_goal(session, level="month", title="July math plan")
        child = create_goal(
            session,
            level="week",
            title="Week 1 calculus",
            parent_id=parent.id,
        )
        task = create_task(
            session,
            goal_id=child.id,
            title="Derivative practice",
            planned_date=date(2026, 7, 14),
            estimated_minutes=40,
            source_type="goal",
            source_id=child.id,
        )
        submission = submit_task_result(
            session,
            task.id,
            result_type="partial",
            completion_ratio=50,
            actual_minutes=25,
            confirmed_at=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
            idempotency_key="goal-rollup",
            request_id="goal-rollup",
        )
        events = list(session.scalars(select(GoalHistoryEvent)).all())

    assert submission.created is True
    assert child.progress == 50
    assert child.actual_minutes == 25
    assert parent.progress == 50
    assert parent.actual_minutes == 25
    assert {event.goal_id for event in events} == {parent.id, child.id}
    assert {event.source_type for event in events} == {"task_result"}
    assert {event.request_id for event in events} == {"goal-rollup"}


def test_goal_recalculate_api_marks_overdue_risk_and_history(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        goal = client.post(
            "/api/v1/goals",
            json={
                "level": "week",
                "title": "Overdue sprint",
                "end_date": "2026-07-13",
            },
        ).json()["data"]
        client.post(
            "/api/v1/tasks",
            json={
                "goal_id": goal["id"],
                "title": "Unfinished overdue task",
                "planned_date": "2026-07-13",
                "estimated_minutes": 30,
                "source_type": "goal",
                "source_id": goal["id"],
            },
        )
        recalculate = client.post(
            f"/api/v1/goals/{goal['id']}/recalculate",
            json={"as_of_date": "2026-07-14", "reason": "weekly risk review"},
            headers={"X-Request-ID": "manual-recalc"},
        )
        history = client.get(f"/api/v1/goals/{goal['id']}/history")

    recalculated = recalculate.json()["data"]
    history_body = history.json()["data"]
    assert recalculate.status_code == 200
    assert recalculate.json()["meta"] == {"request_id": "manual-recalc"}
    assert recalculated["root"]["risk_status"] == "high"
    assert recalculated["root"]["status"] == "delayed"
    assert recalculated["total_events"] == 1
    assert recalculated["events"][0]["previous_risk_status"] == "normal"
    assert recalculated["events"][0]["new_risk_status"] == "high"
    assert recalculated["events"][0]["reason"] == "weekly risk review"
    assert history.status_code == 200
    assert history_body["total"] == 1
    assert history_body["items"][0]["request_id"] == "manual-recalc"
