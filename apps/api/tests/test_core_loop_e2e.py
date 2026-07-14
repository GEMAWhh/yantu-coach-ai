from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.files.backup import create_backup, restore_backup
from app.main import create_app
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


def _data(response: Response) -> dict[str, Any]:
    body = response.json()
    assert response.status_code == 200
    return body["data"]


def _create_knowledge_node(client: TestClient) -> str:
    subject = _data(
        client.post(
            "/api/v1/knowledge/nodes",
            json={"code": "loop.math", "name": "Math", "node_type": "subject"},
        )
    )
    module = _data(
        client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "loop.math.module",
                "name": "Module",
                "node_type": "module",
                "parent_id": subject["id"],
            },
        )
    )
    chapter = _data(
        client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "loop.math.module.chapter",
                "name": "Chapter",
                "node_type": "chapter",
                "parent_id": module["id"],
            },
        )
    )
    node = _data(
        client.post(
            "/api/v1/knowledge/nodes",
            json={
                "code": "loop.math.module.chapter.node",
                "name": "Derivative application",
                "node_type": "knowledge",
                "parent_id": chapter["id"],
                "importance": 90,
            },
        )
    )
    return str(node["id"])


def _add_evidence(
    client: TestClient,
    node_id: str,
    evidence_type: str,
    **payload: object,
) -> str:
    response = _data(
        client.post(
            f"/api/v1/knowledge/nodes/{node_id}/evidence",
            json={"evidence_type": evidence_type, "source_type": "core-loop", **payload},
        )
    )
    return str(response["id"])


def _evaluate(client: TestClient, node_id: str, target_stage: int) -> dict[str, Any]:
    return _data(
        client.post(
            f"/api/v1/knowledge/nodes/{node_id}/evaluate",
            json={"target_stage": target_stage},
        )
    )


def test_core_learning_loop_normal_failure_duplicate_and_restore(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        node_id = _create_knowledge_node(client)

        _add_evidence(client, node_id, "reading", occurred_at="2026-01-01T08:00:00Z")
        exposed = _evaluate(client, node_id, 1)
        blocked_recall = _evaluate(client, node_id, 2)

        assert exposed["new_stage"] == 1
        assert blocked_recall["changed"] is False
        assert "MISSING_SELF_EXPLANATION" in blocked_recall["blocking_reasons"]

        _add_evidence(
            client,
            node_id,
            "self_explanation",
            score=90,
            occurred_at="2026-01-01T09:00:00Z",
        )
        _add_evidence(
            client,
            node_id,
            "closed_book_recall",
            score=90,
            hint_level=0,
            occurred_at="2026-01-01T10:00:00Z",
        )
        _add_evidence(
            client,
            node_id,
            "basic_question",
            sample_count=4,
            correct_count=4,
            accuracy=100,
            occurred_at="2026-01-01T11:00:00Z",
        )
        _add_evidence(
            client,
            node_id,
            "variant_question",
            sample_count=3,
            correct_count=3,
            accuracy=100,
            is_original=False,
            occurred_at="2026-01-01T12:00:00Z",
        )
        _add_evidence(
            client,
            node_id,
            "integrated_question",
            sample_count=2,
            correct_count=2,
            accuracy=100,
            occurred_at="2026-01-01T13:00:00Z",
        )
        _add_evidence(
            client,
            node_id,
            "closed_book_recall",
            score=92,
            hint_level=0,
            occurred_at="2026-01-02T10:00:00Z",
        )
        for stage in range(2, 8):
            assert _evaluate(client, node_id, stage)["new_stage"] == stage

        goal = _data(
            client.post(
                "/api/v1/goals",
                json={
                    "level": "week",
                    "title": "Core loop weekly goal",
                    "estimated_minutes": 80,
                },
            )
        )
        task = _data(
            client.post(
                "/api/v1/tasks",
                json={
                    "goal_id": goal["id"],
                    "knowledge_node_id": node_id,
                    "subject_id": "math",
                    "title": "Closed-loop recall task",
                    "planned_date": "2026-07-14",
                    "estimated_minutes": 40,
                    "source_type": "goal",
                    "source_id": goal["id"],
                    "reason": "Normal path task result should not directly alter mastery",
                },
            )
        )
        first_result = _data(
            client.post(
                f"/api/v1/tasks/{task['id']}/results",
                json={
                    "result_type": "completed",
                    "completion_ratio": 100,
                    "actual_minutes": 50,
                    "accuracy": 90,
                },
                headers={"Idempotency-Key": "core-loop-task-result"},
            )
        )
        duplicate_result = _data(
            client.post(
                f"/api/v1/tasks/{task['id']}/results",
                json={
                    "result_type": "completed",
                    "completion_ratio": 100,
                    "actual_minutes": 50,
                },
                headers={"Idempotency-Key": "core-loop-task-result"},
            )
        )
        assert first_result["created"] is True
        assert duplicate_result["created"] is False
        assert duplicate_result["result"]["id"] == first_result["result"]["id"]

        generated = _data(
            client.post(
                "/api/v1/today/generate",
                json={
                    "available_minutes": 240,
                    "energy": "medium",
                    "subject_filter": "math",
                    "candidates": [
                        {
                            "id": "math-review",
                            "title": "Math review",
                            "subject_id": "math",
                            "estimated_minutes": 60,
                            "cognitive_load": "medium",
                        },
                        {
                            "id": "course-841",
                            "title": "841 task",
                            "subject_id": "841",
                            "estimated_minutes": 60,
                            "cognitive_load": "medium",
                        },
                    ],
                },
            )
        )
        assert generated["schedulable_minutes"] == 196
        assert generated["selected"][0]["id"] == "math-review"
        rejected = {item["id"]: item["reasons"] for item in generated["rejected"]}
        assert rejected["course-841"] == ["SUBJECT_FILTER_MISMATCH"]

        backup = create_backup(test_settings, label="core-loop")

        schedules = _data(client.post("/api/v1/reviews/recalculate"))
        schedule_id = schedules["items"][0]["id"]
        failed_review = _data(
            client.post(
                f"/api/v1/reviews/{schedule_id}/results",
                json={
                    "result_type": "fail",
                    "score": 40,
                    "sample_count": 3,
                    "correct_count": 1,
                    "accuracy": 33,
                    "occurred_at": "2026-08-20T09:00:00Z",
                },
                headers={"Idempotency-Key": "failed-review"},
            )
        )
        assert failed_review["evaluation_new_stage"] == 8

        due_reviews = _data(client.get("/api/v1/reviews/due?date=2026-08-21"))
        assert due_reviews["total"] == 1
        assert due_reviews["items"][0]["candidate"]["source_type"] == "review_schedule"

        restore_backup(test_settings, backup.path)
        restored_history = _data(client.get(f"/api/v1/knowledge/nodes/{node_id}/history"))
        assert restored_history["items"][-1]["stage"] == 7
        restored_today = _data(client.get("/api/v1/today?date=2026-07-14"))
        assert restored_today["total_tasks"] == 1
