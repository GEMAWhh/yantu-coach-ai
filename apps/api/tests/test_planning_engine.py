from collections.abc import Generator
from dataclasses import asdict
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.planning.engine import CognitiveLoad, PlanningCandidate, generate_today_plan
from app.settings import RuntimeSettings, get_settings


@pytest.fixture
def test_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[RuntimeSettings, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def _candidate(
    candidate_id: str,
    *,
    subject_id: str = "math",
    estimated_minutes: int = 60,
    cognitive_load: CognitiveLoad = "medium",
    prerequisite_status: str = "satisfied",
    failure_streak: int = 0,
    overtime_count: int = 0,
    deadline_urgency: int = 50,
    review_due: int = 50,
    knowledge_importance: int = 50,
) -> PlanningCandidate:
    return PlanningCandidate(
        id=candidate_id,
        title=f"Task {candidate_id}",
        subject_id=subject_id,
        estimated_minutes=estimated_minutes,
        cognitive_load=cognitive_load,
        prerequisite_status=prerequisite_status,
        source_type="goal",
        source_id="goal-1",
        failure_streak=failure_streak,
        overtime_count=overtime_count,
        deadline_urgency=deadline_urgency,
        review_due=review_due,
        knowledge_importance=knowledge_importance,
        weakness=30,
        parent_goal_risk=20,
        repeat_error=10,
    )


def test_plan_004_keeps_configured_buffer() -> None:
    plan = generate_today_plan(
        [_candidate(f"t{i}", estimated_minutes=60) for i in range(1, 6)],
        available_minutes=240,
        energy="medium",
    )

    assert plan.schedulable_minutes == 196
    assert plan.planned_minutes <= 196
    assert plan.buffer_minutes >= 44
    assert all(item.score.breakdown for item in plan.selected)
    assert any("INSUFFICIENT_CAPACITY_AFTER_BUFFER" in item.reasons for item in plan.rejected)


def test_plan_005_respects_single_subject_filter() -> None:
    plan = generate_today_plan(
        [
            _candidate("math-1", subject_id="math"),
            _candidate("course-841", subject_id="841", deadline_urgency=100),
        ],
        available_minutes=180,
        energy="medium",
        subject_filter="math",
    )

    assert {item.candidate.subject_id for item in plan.selected} == {"math"}
    rejected = {item.candidate.id: item.reasons for item in plan.rejected}
    assert rejected["course-841"] == ["SUBJECT_FILTER_MISMATCH"]


def test_plan_006_low_energy_blocks_high_cognitive_work() -> None:
    plan = generate_today_plan(
        [
            _candidate("high", cognitive_load="high", deadline_urgency=100),
            _candidate("low", cognitive_load="low", deadline_urgency=20),
        ],
        available_minutes=180,
        energy="low",
    )

    assert [item.candidate.id for item in plan.selected] == ["low"]
    rejected = {item.candidate.id: item.reasons for item in plan.rejected}
    assert rejected["high"] == ["LOW_ENERGY_BLOCKS_HIGH_COGNITIVE_LOAD"]


def test_prerequisite_unmet_task_is_rejected_with_reason() -> None:
    plan = generate_today_plan(
        [
            _candidate("blocked", prerequisite_status="unmet", deadline_urgency=100),
            _candidate("ready", deadline_urgency=20),
        ],
        available_minutes=180,
        energy="medium",
    )

    assert [item.candidate.id for item in plan.selected] == ["ready"]
    rejected = {item.candidate.id: item for item in plan.rejected}
    assert rejected["blocked"].reasons == ["PREREQUISITE_NOT_MET"]
    assert rejected["blocked"].score.breakdown


def test_plan_007_overtime_task_is_split_to_max_single_task_minutes() -> None:
    plan = generate_today_plan(
        [
            _candidate(
                "overtime",
                estimated_minutes=90,
                overtime_count=2,
                deadline_urgency=100,
            )
        ],
        available_minutes=120,
        energy="medium",
    )

    assert len(plan.selected) == 1
    assert plan.selected[0].scheduled_minutes == 60
    assert "TASK_SPLIT_BY_OVERTIME" in plan.selected[0].explanations


def test_plan_008_repeated_noncompletion_requires_diagnosis() -> None:
    plan = generate_today_plan(
        [
            _candidate("stuck", failure_streak=3, deadline_urgency=100),
            _candidate("fallback", deadline_urgency=20),
        ],
        available_minutes=180,
        energy="medium",
    )

    assert [item.candidate.id for item in plan.selected] == ["fallback"]
    rejected = {item.candidate.id: item.reasons for item in plan.rejected}
    assert rejected["stuck"] == ["REPEATED_NONCOMPLETION_REQUIRES_DIAGNOSIS"]


def test_today_generate_api_returns_selected_and_rejected_reasons(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/today/generate",
            json={
                "available_minutes": 120,
                "energy": "low",
                "subject_filter": "math",
                "candidates": [
                    asdict(_candidate("math-low", subject_id="math", cognitive_load="low")),
                    asdict(_candidate("math-high", subject_id="math", cognitive_load="high")),
                    asdict(_candidate("course-841", subject_id="841", cognitive_load="low")),
                ],
            },
            headers={"X-Request-ID": "planning-engine"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["meta"] == {"request_id": "planning-engine"}
    assert body["data"]["rule_version"] == "planning-v1.0.0"
    assert body["data"]["selected"][0]["id"] == "math-low"
    rejected = {item["id"]: item["reasons"] for item in body["data"]["rejected"]}
    assert rejected["math-high"] == ["LOW_ENERGY_BLOCKS_HIGH_COGNITIVE_LOAD"]
    assert rejected["course-841"] == ["SUBJECT_FILTER_MISMATCH"]
    assert all(item["score"]["breakdown"] for item in body["data"]["rejected"])
