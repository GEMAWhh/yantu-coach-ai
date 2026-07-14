from collections.abc import Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.knowledge.service import create_knowledge_node
from app.main import create_app
from app.mastery.service import create_mastery_evidence, evaluate_mastery, get_mastery_history
from app.models.knowledge import KnowledgeNode
from app.models.review import ReviewResult
from app.reviews.service import (
    ensure_review_schedule,
    list_due_reviews,
    submit_review_result,
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


def _occurred(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=UTC)


def _create_knowledge(session: Session, suffix: str = "review") -> KnowledgeNode:
    subject = create_knowledge_node(
        session, code=f"{suffix}.math", name="Math", node_type="subject"
    )
    module = create_knowledge_node(
        session,
        code=f"{suffix}.math.module",
        name="Module",
        node_type="module",
        parent_id=subject.id,
    )
    chapter = create_knowledge_node(
        session,
        code=f"{suffix}.math.module.chapter",
        name="Chapter",
        node_type="chapter",
        parent_id=module.id,
    )
    return create_knowledge_node(
        session,
        code=f"{suffix}.math.module.chapter.node",
        name="Derivative application",
        node_type="knowledge",
        parent_id=chapter.id,
        importance=80,
    )


def _add_evidence_for_stage(session: Session, node_id: str, target_stage: int) -> None:
    create_mastery_evidence(
        session,
        knowledge_node_id=node_id,
        evidence_type="reading",
        source_type="test",
        occurred_at=_occurred(1),
    )
    if target_stage >= 2:
        create_mastery_evidence(
            session,
            knowledge_node_id=node_id,
            evidence_type="self_explanation",
            source_type="test",
            score=90,
            occurred_at=_occurred(1),
        )
    if target_stage >= 3:
        create_mastery_evidence(
            session,
            knowledge_node_id=node_id,
            evidence_type="closed_book_recall",
            source_type="test",
            score=90,
            hint_level=0,
            occurred_at=_occurred(1),
        )
    if target_stage >= 4:
        create_mastery_evidence(
            session,
            knowledge_node_id=node_id,
            evidence_type="basic_question",
            source_type="test",
            sample_count=4,
            correct_count=4,
            accuracy=100,
            occurred_at=_occurred(1),
        )
    for stage in range(1, target_stage + 1):
        result = evaluate_mastery(session, node_id, target_stage=stage)
        assert result.new_stage == stage


def test_review_schedule_uses_stage_base_intervals(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        schedule = ensure_review_schedule(
            session,
            knowledge_node_id=node.id,
            stage=4,
            reviewed_at=_occurred(1),
        )
        stage_four_interval = schedule.interval_days
        stage_four_due_date = schedule.due_at.date()
        updated = ensure_review_schedule(
            session,
            knowledge_node_id=node.id,
            stage=5,
            reviewed_at=_occurred(1),
        )

    assert schedule.id == updated.id
    assert stage_four_interval == 7
    assert stage_four_due_date == date(2026, 1, 8)
    assert updated.interval_days == 14
    assert updated.due_at.date() == date(2026, 1, 15)
    assert updated.next_reason == "base_interval:variant_application"


def test_failed_review_rolls_back_and_shortens_interval(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_evidence_for_stage(session, node.id, 4)
        schedule = ensure_review_schedule(
            session,
            knowledge_node_id=node.id,
            stage=4,
            reviewed_at=_occurred(1),
        )
        submission = submit_review_result(
            session,
            schedule.id,
            result_type="fail",
            score=40,
            sample_count=5,
            correct_count=2,
            accuracy=40,
            occurred_at=_occurred(8),
            idempotency_key="failed-review",
        )
        history = get_mastery_history(session, node.id)

    assert submission.created is True
    assert submission.evaluation is not None
    assert submission.evaluation.new_stage == 3
    assert submission.schedule.current_stage == 3
    assert submission.schedule.interval_days < 7
    assert submission.schedule.due_at.date() == date(2026, 1, 9)
    assert submission.result.evidence_id is not None
    assert history[-1].transition_reason == "review_failed_regression"


def test_independent_pass_extends_interval_and_same_day_redo_does_not_count(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session)
        _add_evidence_for_stage(session, node.id, 3)
        schedule = ensure_review_schedule(
            session,
            knowledge_node_id=node.id,
            stage=3,
            reviewed_at=_occurred(1),
        )
        first = submit_review_result(
            session,
            schedule.id,
            result_type="pass",
            score=90,
            occurred_at=_occurred(4),
            idempotency_key="pass-1",
        )
        duplicate = submit_review_result(
            session,
            schedule.id,
            result_type="pass",
            score=90,
            occurred_at=_occurred(4),
            idempotency_key="pass-1",
        )
        redo = submit_review_result(
            session,
            schedule.id,
            result_type="pass",
            score=95,
            occurred_at=_occurred(4),
            idempotency_key="same-day-redo",
        )
        result_count = session.scalar(select(func.count(ReviewResult.id)))

    assert first.created is True
    assert first.result.independent_timepoint is True
    assert first.schedule.pass_streak == 1
    assert first.schedule.interval_days == 6
    assert first.schedule.due_at.date() == date(2026, 1, 10)
    assert duplicate.created is False
    assert duplicate.result.id == first.result.id
    assert redo.created is True
    assert redo.result.independent_timepoint is False
    assert redo.result.evidence_id is None
    assert redo.schedule.pass_streak == 1
    assert result_count == 2


def test_due_reviews_enter_planning_candidates(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        due_node = _create_knowledge(session, "due")
        future_node = _create_knowledge(session, "future")
        due_schedule = ensure_review_schedule(
            session,
            knowledge_node_id=due_node.id,
            stage=3,
            reviewed_at=_occurred(1),
        )
        ensure_review_schedule(
            session,
            knowledge_node_id=future_node.id,
            stage=7,
            reviewed_at=_occurred(1),
        )
        due_items = list_due_reviews(session, due_on=date(2026, 1, 4))

    assert len(due_items) == 1
    assert due_items[0].schedule.id == due_schedule.id
    assert due_items[0].candidate.source_type == "review_schedule"
    assert due_items[0].candidate.source_id == due_schedule.id
    assert due_items[0].candidate.review_due == 100
    assert due_items[0].candidate.estimated_minutes == 20


def test_review_api_lists_due_and_submits_idempotent_result(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        node = _create_knowledge(session, "api-review")
        schedule = ensure_review_schedule(
            session,
            knowledge_node_id=node.id,
            stage=3,
            reviewed_at=_occurred(1),
        )

    with TestClient(create_app()) as client:
        due_response = client.get(
            "/api/v1/reviews/due?date=2026-01-04",
            headers={"X-Request-ID": "due-reviews"},
        )
        first_response = client.post(
            f"/api/v1/reviews/{schedule.id}/results",
            json={
                "result_type": "pass",
                "score": 88,
                "occurred_at": "2026-01-04T09:00:00Z",
            },
            headers={"Idempotency-Key": "review-result", "X-Request-ID": "review-result"},
        )
        second_response = client.post(
            f"/api/v1/reviews/{schedule.id}/results",
            json={
                "result_type": "pass",
                "score": 88,
                "occurred_at": "2026-01-04T09:00:00Z",
            },
            headers={"Idempotency-Key": "review-result"},
        )

    due_body = due_response.json()
    first_body = first_response.json()
    second_body = second_response.json()
    assert due_response.status_code == 200
    assert due_body["meta"] == {"request_id": "due-reviews"}
    assert due_body["data"]["items"][0]["candidate"]["source_type"] == "review_schedule"
    assert due_body["data"]["items"][0]["candidate"]["source_id"] == schedule.id
    assert first_response.status_code == 200
    assert first_body["meta"] == {"request_id": "review-result"}
    assert first_body["data"]["created"] is True
    assert first_body["data"]["result"]["independent_timepoint"] is True
    assert second_response.status_code == 200
    assert second_body["data"]["created"] is False
    assert second_body["data"]["result"]["id"] == first_body["data"]["result"]["id"]
