from collections.abc import Generator
from datetime import UTC, date, datetime
from math import ceil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.main import create_app
from app.models.time_calibration import TimeAdjustment, TimeCoefficient
from app.planning.service import create_task, submit_task_result
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


def _create_task(
    session: Session,
    *,
    subject_id: str = "math",
    task_type: str = "study",
    difficulty: str | None = None,
    estimated_minutes: int = 60,
) -> str:
    task = create_task(
        session,
        title=f"{subject_id}-{task_type}",
        planned_date=date(2026, 7, 14),
        estimated_minutes=estimated_minutes,
        source_type="test",
        subject_id=subject_id,
        task_type=task_type,
        difficulty=difficulty,
    )
    return task.id


def _submit(
    session: Session,
    task_id: str,
    *,
    actual_minutes: int,
    idempotency_key: str | None = None,
) -> None:
    submit_task_result(
        session,
        task_id,
        result_type="completed",
        completion_ratio=100,
        actual_minutes=actual_minutes,
        confirmed_at=datetime(2026, 7, 14, 9, 0, tzinfo=UTC),
        idempotency_key=idempotency_key,
    )


def _coefficient(session: Session, task_type: str = "study") -> TimeCoefficient:
    coefficient = session.scalar(
        select(TimeCoefficient).where(
            TimeCoefficient.subject_id == "math",
            TimeCoefficient.task_type == task_type,
            TimeCoefficient.difficulty == "default",
        )
    )
    assert coefficient is not None
    return coefficient


def test_actual_estimated_ratio_updates_personal_coefficient(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        task_id = _create_task(session, estimated_minutes=60)
        _submit(session, task_id, actual_minutes=90)
        coefficient = _coefficient(session)
        adjustment = session.scalar(select(TimeAdjustment))

    assert coefficient.sample_count == 1
    assert coefficient.coefficient == 1.15
    assert coefficient.last_ratio == 1.5
    assert coefficient.overtime_streak == 1
    assert adjustment is not None
    assert adjustment.previous_coefficient == 1.0
    assert adjustment.new_coefficient == 1.15
    assert adjustment.ignored is False


def test_extreme_and_zero_duration_are_recorded_but_ignored(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        extreme_task = _create_task(session, estimated_minutes=60)
        zero_task = _create_task(session, task_type="review", estimated_minutes=60)
        _submit(session, extreme_task, actual_minutes=400)
        _submit(session, zero_task, actual_minutes=0)
        adjustments = {
            item.task_type: item for item in session.scalars(select(TimeAdjustment)).all()
        }
        study = _coefficient(session, "study")
        review = _coefficient(session, "review")

    assert study.coefficient == 1.0
    assert study.sample_count == 0
    assert review.coefficient == 1.0
    assert review.sample_count == 0
    assert adjustments["study"].ignored is True
    assert adjustments["study"].ignore_reason == "EXTREME_RATIO"
    assert adjustments["review"].ignored is True
    assert adjustments["review"].ignore_reason == "ZERO_DURATION"


def test_duplicate_task_result_does_not_create_second_adjustment(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        task_id = _create_task(session)
        first = submit_task_result(
            session,
            task_id,
            result_type="completed",
            completion_ratio=100,
            actual_minutes=90,
            idempotency_key="same-result",
        )
        second = submit_task_result(
            session,
            task_id,
            result_type="completed",
            completion_ratio=100,
            actual_minutes=90,
            idempotency_key="same-result",
        )
        adjustment_count = session.scalar(select(func.count(TimeAdjustment.id)))
        coefficient = _coefficient(session)

    assert first.created is True
    assert second.created is False
    assert second.result.id == first.result.id
    assert adjustment_count == 1
    assert coefficient.sample_count == 1


def test_different_task_types_are_isolated(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        study_task = _create_task(session, task_type="study", estimated_minutes=60)
        review_task = _create_task(session, task_type="review", estimated_minutes=60)
        _submit(session, study_task, actual_minutes=90)
        _submit(session, review_task, actual_minutes=30)
        study = _coefficient(session, "study")
        review = _coefficient(session, "review")

    assert study.coefficient == 1.15
    assert review.coefficient == 0.85
    assert study.overtime_streak == 1
    assert review.overtime_streak == 0


def test_consecutive_overtime_suggests_split(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        first_task = _create_task(session, estimated_minutes=60)
        second_task = _create_task(session, estimated_minutes=60)
        _submit(session, first_task, actual_minutes=90)
        _submit(session, second_task, actual_minutes=90)
        statement = select(TimeAdjustment).order_by(TimeAdjustment.created_at)
        adjustments = list(session.scalars(statement).all())
        coefficient = _coefficient(session)

    assert coefficient.overtime_streak == 2
    assert adjustments[0].suggested_split is False
    assert adjustments[1].suggested_split is True


def test_today_generate_reads_latest_time_coefficient(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        task_id = _create_task(session, estimated_minutes=40)
        _submit(session, task_id, actual_minutes=80)
        coefficient = _coefficient(session)

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/today/generate",
            json={
                "available_minutes": 120,
                "energy": "medium",
                "candidates": [
                    {
                        "id": "math-study",
                        "title": "Math study",
                        "subject_id": "math",
                        "estimated_minutes": 40,
                        "cognitive_load": "medium",
                        "task_type": "study",
                    }
                ],
            },
        )
        coefficients = client.get("/api/v1/time-calibration/coefficients")
        adjustments = client.get("/api/v1/time-calibration/adjustments")

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["selected"][0]["scheduled_minutes"] == ceil(40 * coefficient.coefficient)
    assert coefficients.status_code == 200
    assert coefficients.json()["data"]["items"][0]["coefficient"] == coefficient.coefficient
    assert adjustments.status_code == 200
    assert adjustments.json()["data"]["items"][0]["raw_ratio"] == 2.0
