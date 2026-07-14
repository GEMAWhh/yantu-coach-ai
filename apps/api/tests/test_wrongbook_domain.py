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
from app.models.audit import AuditEvent
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


def test_wrongbook_result_shortcuts_submit_fixed_attempt_types(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client)
        _submit_attempt(client, wrong_id, "no_hint_redo", True)
        variant = client.post(
            f"/api/v1/wrongbook/{wrong_id}/variant-results",
            json={"is_correct": True, "score": 96, "confidence": 80},
            headers={"Idempotency-Key": "variant-shortcut"},
        )
        interval = client.post(
            f"/api/v1/wrongbook/{wrong_id}/interval-results",
            json={"is_correct": True, "answer_text": "reviewed without hints"},
            headers={"Idempotency-Key": "interval-shortcut", "X-Request-ID": "interval-result"},
        )
        duplicate_interval = client.post(
            f"/api/v1/wrongbook/{wrong_id}/interval-results",
            json={"is_correct": True, "answer_text": "reviewed without hints"},
            headers={"Idempotency-Key": "interval-shortcut"},
        )
        history = client.get(f"/api/v1/wrongbook/{wrong_id}/history")

    assert variant.status_code == 200
    variant_body = variant.json()["data"]
    assert variant_body["attempt"]["attempt_type"] == "variant"
    assert variant_body["attempt"]["score"] == 96
    assert variant_body["record"]["current_status"] == "pending_interval"
    assert interval.status_code == 200
    interval_body = interval.json()["data"]
    assert interval_body["attempt"]["attempt_type"] == "interval_test"
    assert interval_body["attempt"]["request_id"] == "interval-result"
    assert interval_body["record"]["current_status"] == "stable_corrected"
    assert duplicate_interval.status_code == 200
    duplicate_body = duplicate_interval.json()["data"]
    assert duplicate_body["created"] is False
    assert duplicate_body["attempt"]["id"] == interval_body["attempt"]["id"]
    history_body = history.json()["data"]
    assert history_body["total_attempts"] == 3
    assert [attempt["attempt_type"] for attempt in history_body["attempts"]] == [
        "no_hint_redo",
        "variant",
        "interval_test",
    ]


def test_wrongbook_ai_draft_requires_confirmation_before_record_mutation(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client, include_causes=False)
        analyzed = client.post(
            f"/api/v1/wrongbook/{wrong_id}/analyze",
            json={"provider_mode": "valid"},
        )
        before_confirm = client.get(f"/api/v1/wrongbook/{wrong_id}")
        fetched_draft = client.get(f"/api/v1/wrongbook/{wrong_id}/draft")
        patched = client.patch(
            f"/api/v1/wrongbook/{wrong_id}/draft",
            json={"structured_json": _wrongbook_draft_payload()},
        )
        confirmed = client.post(
            f"/api/v1/wrongbook/{wrong_id}/confirm",
            headers={"X-Request-ID": "wrongbook-confirm"},
        )
        repeated = client.post(f"/api/v1/wrongbook/{wrong_id}/confirm")

    assert analyzed.status_code == 200
    analyzed_body = analyzed.json()["data"]
    assert analyzed_body["draft"]["status"] == "draft"
    assert analyzed_body["draft"]["validation_errors"] == []
    assert analyzed_body["ai_job"]["job_type"] == "wrongbook_analysis"
    assert analyzed_body["ai_job"]["status"] == "succeeded"
    assert before_confirm.status_code == 200
    before_record = before_confirm.json()["data"]["record"]
    assert before_record["current_status"] == "pending_analysis"
    assert before_record["surface_cause"] is None
    assert before_record["deep_cause"] is None
    assert before_record["prerequisite_gap"] is None
    assert fetched_draft.status_code == 200
    assert fetched_draft.json()["data"]["id"] == analyzed_body["draft"]["id"]
    assert patched.status_code == 200
    assert patched.json()["data"]["structured_json"]["surface_cause"] == "sign error"
    assert confirmed.status_code == 200
    confirmed_body = confirmed.json()["data"]
    assert confirmed_body["created"] is True
    assert confirmed_body["draft"]["status"] == "confirmed"
    assert confirmed_body["draft"]["confirmed_once"] is True
    assert confirmed_body["record"]["surface_cause"] == "sign error"
    assert confirmed_body["record"]["deep_cause"] == "chain rule retrieval failed"
    assert confirmed_body["record"]["prerequisite_gap"] == "derivative chain rule"
    assert confirmed_body["record"]["current_status"] == "pending_no_hint_redo"
    assert repeated.status_code == 200
    assert repeated.json()["data"]["created"] is False

    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        audit_events = list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.event_type == "wrongbook.draft_confirmed",
                    AuditEvent.object_id == wrong_id,
                )
            ).all()
        )
    assert len(audit_events) == 1
    assert audit_events[0].request_id == "wrongbook-confirm"


def test_invalid_wrongbook_ai_draft_cannot_confirm_or_mutate_record(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        wrong_id = _create_wrong_record(client, include_causes=False)
        invalid = client.post(
            f"/api/v1/wrongbook/{wrong_id}/analyze",
            json={"provider_mode": "invalid_schema"},
        )
        blocked = client.post(f"/api/v1/wrongbook/{wrong_id}/confirm")
        after_blocked = client.get(f"/api/v1/wrongbook/{wrong_id}")
        patched = client.patch(
            f"/api/v1/wrongbook/{wrong_id}/draft",
            json={"structured_json": _wrongbook_draft_payload()},
        )
        confirmed = client.post(f"/api/v1/wrongbook/{wrong_id}/confirm")

    assert invalid.status_code == 200
    invalid_body = invalid.json()["data"]
    assert invalid_body["draft"]["status"] == "needs_correction"
    assert invalid_body["draft"]["validation_errors"]
    assert invalid_body["ai_job"]["status"] == "failed"
    assert invalid_body["ai_job"]["error_code"] == "AI_OUTPUT_SCHEMA_INVALID"
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "AI_DRAFT_NOT_CONFIRMED"
    blocked_record = after_blocked.json()["data"]["record"]
    assert blocked_record["current_status"] == "pending_analysis"
    assert blocked_record["surface_cause"] is None
    assert blocked_record["deep_cause"] is None
    assert patched.status_code == 200
    assert patched.json()["data"]["status"] == "draft"
    assert patched.json()["data"]["validation_errors"] == []
    assert confirmed.status_code == 200
    assert confirmed.json()["data"]["record"]["surface_cause"] == "sign error"


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


def _create_wrong_record(
    client: TestClient,
    knowledge_node_id: str | None = None,
    *,
    include_causes: bool = True,
) -> str:
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
    record_payload: dict[str, Any] = {"question_id": question_id}
    if include_causes:
        record_payload.update(
            {
                "surface_cause": "calculation slip",
                "deep_cause": "derivative rule not automatic",
                "prerequisite_gap": "power rule",
            }
        )
    record_response = client.post("/api/v1/wrongbook/records", json=record_payload)
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


def _wrongbook_draft_payload() -> dict[str, Any]:
    return {
        "surface_cause": "sign error",
        "deep_cause": "chain rule retrieval failed",
        "prerequisite_gap": "derivative chain rule",
        "remediation_plan": [
            {
                "action": "redo_without_hints",
                "reason": "confirm independent retrieval",
                "priority": "high",
            }
        ],
        "uncertain_fields": [
            {
                "field": "source_image",
                "reason": "manual confirmation required",
                "confidence": 0.4,
            }
        ],
    }
