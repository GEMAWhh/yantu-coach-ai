from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.files.storage import store_original_file
from app.knowledge.service import create_knowledge_node
from app.main import create_app
from app.models.asset import Asset
from app.models.knowledge import KnowledgeNode
from app.models.wrongbook import QuestionAsset, WrongRecord, WrongVerification
from app.settings import RuntimeSettings, get_settings

PNG_BYTES = b"\x89PNG\r\n\x1a\nwrongbook-test-png"
ASSET_ROLES = [
    "statement",
    "figure",
    "my_answer",
    "marking",
    "standard_answer",
    "original_solution",
    "supplement",
]


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


def test_wrongbook_assets_are_strictly_role_separated(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        asset = _create_asset(test_settings, session, tmp_path)

    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client)
        linked = [
            client.post(
                f"/api/v1/wrongbook/{wrong_id}/assets",
                json={"asset_id": asset.id, "asset_role": role, "page_order": 0},
            )
            for role in ASSET_ROLES
        ]
        duplicate = client.post(
            f"/api/v1/wrongbook/{wrong_id}/assets",
            json={"asset_id": asset.id, "asset_role": "statement", "page_order": 0},
        )
        invalid = client.post(
            f"/api/v1/wrongbook/{wrong_id}/assets",
            json={"asset_id": asset.id, "asset_role": "answer", "page_order": 0},
        )

    assert [response.status_code for response in linked] == [200] * len(ASSET_ROLES)
    assert {response.json()["data"]["asset_role"] for response in linked} == set(ASSET_ROLES)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "QUESTION_ASSET_DUPLICATE_ROLE_PAGE"
    assert invalid.status_code == 422

    with session_factory() as session:
        roles = set(session.scalars(select(QuestionAsset.asset_role)).all())
    assert roles == set(ASSET_ROLES)


def test_original_redo_and_missing_verification_cannot_resolve_wrong_record(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client)
        original = _submit_attempt(client, wrong_id, "original_redo", True)
        variant = _submit_attempt(client, wrong_id, "variant", True)
        interval = _submit_attempt(client, wrong_id, "interval_test", True)
        no_hint = client.post(
            f"/api/v1/wrongbook/{wrong_id}/attempts",
            json={"attempt_type": "no_hint_redo", "is_correct": True},
            headers={"Idempotency-Key": "no-hint-pass", "X-Request-ID": "wrong-no-hint"},
        )
        duplicate = client.post(
            f"/api/v1/wrongbook/{wrong_id}/attempts",
            json={"attempt_type": "no_hint_redo", "is_correct": True},
            headers={"Idempotency-Key": "no-hint-pass"},
        )
        history = client.get(f"/api/v1/wrongbook/{wrong_id}/history")

    assert original["record"]["current_status"] == "pending_variant"
    assert original["verification"]["original_redo_passed"] is True
    assert original["verification"]["no_hint_redo_passed"] is False
    assert variant["record"]["current_status"] == "pending_variant"
    assert interval["record"]["current_status"] == "pending_variant"
    no_hint_body = no_hint.json()
    duplicate_body = duplicate.json()
    assert no_hint.status_code == 200
    assert no_hint_body["meta"] == {"request_id": "wrong-no-hint"}
    assert no_hint_body["data"]["created"] is True
    assert no_hint_body["data"]["record"]["current_status"] == "stable_corrected"
    assert duplicate.status_code == 200
    assert duplicate_body["data"]["created"] is False
    assert duplicate_body["data"]["attempt"]["id"] == no_hint_body["data"]["attempt"]["id"]
    history_body = history.json()
    assert history.status_code == 200
    assert history_body["data"]["record"]["current_status"] == "stable_corrected"
    assert (
        history_body["data"]["verification"]["last_attempt_id"]
        == no_hint_body["data"]["attempt"]["id"]
    )
    assert history_body["data"]["total_attempts"] == 4
    assert [attempt["attempt_type"] for attempt in history_body["data"]["attempts"]] == [
        "original_redo",
        "variant",
        "interval_test",
        "no_hint_redo",
    ]
    assert history_body["data"]["attempts"][-1]["request_id"] == "wrong-no-hint"

    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        wrong = session.get(WrongRecord, wrong_id)
        verification = session.scalar(
            select(WrongVerification).where(WrongVerification.wrong_record_id == wrong_id)
        )
    assert wrong is not None
    assert wrong.redo_count == 4
    assert verification is not None
    assert verification.no_hint_redo_passed is True
    assert verification.variant_passed is True
    assert verification.interval_test_passed is True


def test_failed_attempt_rolls_back_and_wrong_record_enters_planning_candidates(
    test_settings: RuntimeSettings,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        knowledge = _create_knowledge(session)

    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client, knowledge_node_id=knowledge.id)
        _submit_attempt(client, wrong_id, "no_hint_redo", True)
        _submit_attempt(client, wrong_id, "variant", True)
        stable = _submit_attempt(client, wrong_id, "interval_test", True)
        failed = _submit_attempt(client, wrong_id, "variant", False)
        candidates = client.get("/api/v1/wrongbook/planning-candidates")

    assert stable["record"]["current_status"] == "stable_corrected"
    assert failed["record"]["current_status"] == "regressed"
    assert failed["record"]["error_count"] == 2
    assert failed["verification"]["variant_passed"] is False
    candidates_body = candidates.json()
    assert candidates.status_code == 200
    assert candidates_body["data"]["total"] == 1
    candidate = candidates_body["data"]["items"][0]
    assert candidate["source_type"] == "wrong_record"
    assert candidate["source_id"] == wrong_id
    assert candidate["subject_id"] == knowledge.subject_id
    assert candidate["repeat_error"] > 0


def _create_knowledge(session: Session) -> KnowledgeNode:
    subject = create_knowledge_node(session, code="wrong.math", name="Math", node_type="subject")
    module = create_knowledge_node(
        session,
        code="wrong.math.module",
        name="Module",
        node_type="module",
        parent_id=subject.id,
    )
    chapter = create_knowledge_node(
        session,
        code="wrong.math.module.chapter",
        name="Chapter",
        node_type="chapter",
        parent_id=module.id,
    )
    return create_knowledge_node(
        session,
        code="wrong.math.module.chapter.node",
        name="Derivative wrongbook",
        node_type="knowledge",
        parent_id=chapter.id,
        importance=90,
    )


def _create_asset(settings: RuntimeSettings, session: Session, tmp_path: Path) -> Asset:
    source = tmp_path / "wrongbook-proof.png"
    source.write_bytes(PNG_BYTES)
    return store_original_file(
        settings,
        session,
        source_path=source,
        original_name="wrongbook-proof.png",
        declared_mime_type="image/png",
    )


def _create_wrong_record(client: TestClient, knowledge_node_id: str | None = None) -> str:
    question_payload: dict[str, Any] = {
        "standard_text": "Find the derivative of x^2 at x=3.",
        "knowledge_node_id": knowledge_node_id,
        "question_type": "calculation",
        "difficulty": "medium",
    }
    if knowledge_node_id is None:
        question_payload["subject_id"] = "math"
    question_response = client.post(
        "/api/v1/wrongbook/questions",
        json=question_payload,
    )
    assert question_response.status_code == 200
    question_id = question_response.json()["data"]["id"]
    record_response = client.post(
        "/api/v1/wrongbook/records",
        json={
            "question_id": question_id,
            "surface_cause": "calculation slip",
            "deep_cause": "derivative rule not automatic",
            "prerequisite_gap": "power rule",
        },
    )
    assert record_response.status_code == 200
    return str(record_response.json()["data"]["record"]["id"])


def _submit_attempt(
    client: TestClient,
    wrong_id: str,
    attempt_type: str,
    is_correct: bool,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/wrongbook/{wrong_id}/attempts",
        json={
            "attempt_type": attempt_type,
            "is_correct": is_correct,
            "score": 100 if is_correct else 30,
        },
    )
    assert response.status_code == 200
    return dict(response.json()["data"])
