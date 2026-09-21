import base64
from collections.abc import Generator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.files.exceptions import PersistentStorageError
from app.main import create_app
from app.models.audit import AuditEvent
from app.models.evidence import AIJob, EvidenceAsset, EvidenceDraft, EvidenceRecord
from app.models.mastery import MasteryEvidence, MasterySnapshot
from app.models.planning import Task
from app.settings import (
    DatabaseBackend,
    RuntimeSettings,
    SupabaseStorageSettings,
    get_settings,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\nevidence-test-png"
JPEG_BYTES = b"\xff\xd8\xff\xe0evidence-test-jpeg"


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


def test_multi_file_upload_links_assets_to_one_evidence_record(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        response = _upload(client)

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["record"]["status"] == "pending"
    assert body["data"]["record"]["asset_count"] == 2
    assert [asset["page_order"] for asset in body["data"]["assets"]] == [0, 1]

    record_id = body["data"]["record"]["id"]
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        linked_count = session.scalar(
            select(func.count(EvidenceAsset.id)).where(
                EvidenceAsset.evidence_record_id == record_id
            )
        )

    assert linked_count == 2


def test_cloud_storage_failure_rolls_back_evidence_record(
    test_settings: RuntimeSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cloud_settings = replace(
        test_settings,
        database_backend=DatabaseBackend.POSTGRESQL,
        supabase_storage=SupabaseStorageSettings(
            "https://example.supabase.co",
            "fake-secret-key-with-at-least-32-characters",
            "yantu-assets",
        ),
    )

    def fail_upload(_self: object, _path: str, _content: bytes, _mime: str) -> None:
        raise PersistentStorageError("cloud object storage upload failed")

    monkeypatch.setattr("app.api.evidence.get_settings", lambda: cloud_settings)
    monkeypatch.setattr("app.files.storage.SupabaseObjectStorage.upload", fail_upload)

    with TestClient(create_app()) as client:
        response = _upload(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CLOUD_FILE_STORAGE_UNAVAILABLE"
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        assert session.scalar(select(func.count(EvidenceRecord.id))) == 0
        assert session.scalar(select(func.count(EvidenceAsset.id))) == 0


def test_fake_provider_creates_schema_valid_draft_without_changing_formal_learning_state(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        upload = _upload(client)
        record_id = upload.json()["data"]["record"]["id"]
        response = client.post(f"/api/v1/evidence/{record_id}/analyze", json={})

    body = response.json()
    assert response.status_code == 200
    assert body["data"]["ai_job"]["provider"] == "fake"
    assert body["data"]["ai_job"]["status"] == "succeeded"
    assert body["data"]["draft"]["status"] == "draft"
    assert body["data"]["draft"]["validation_errors"] == []
    assert set(body["data"]["draft"]["structured_json"]) == {
        "confirmed_facts",
        "inferences",
        "uncertain_fields",
        "teaching_judgment",
        "suggested_actions",
    }

    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        record = session.get(EvidenceRecord, record_id)
        task_count = session.scalar(select(func.count(Task.id)))
        evidence_count = session.scalar(select(func.count(MasteryEvidence.id)))
        snapshot_count = session.scalar(select(func.count(MasterySnapshot.id)))

    assert record is not None
    assert record.status == "pending"
    assert record.confirmed_facts_json is None
    assert task_count == 0
    assert evidence_count == 0
    assert snapshot_count == 0


def test_confirm_is_idempotent_and_audited_once(test_settings: RuntimeSettings) -> None:
    with TestClient(create_app()) as client:
        upload = _upload(client)
        record_id = upload.json()["data"]["record"]["id"]
        client.post(f"/api/v1/evidence/{record_id}/analyze", json={})
        first = client.post(
            f"/api/v1/evidence/{record_id}/confirm",
            headers={"X-Request-ID": "confirm-evidence"},
        )
        second = client.post(f"/api/v1/evidence/{record_id}/confirm")

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 200
    assert first_body["meta"] == {"request_id": "confirm-evidence"}
    assert first_body["data"]["created"] is True
    assert first_body["data"]["record"]["status"] == "confirmed"
    assert first_body["data"]["record"]["confirmed_facts"]["asset_count"] == 2
    assert second.status_code == 200
    assert second_body["data"]["created"] is False
    assert second_body["data"]["record"]["id"] == record_id

    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        audit_count = session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "evidence.confirmed",
                AuditEvent.object_id == record_id,
            )
        )

    assert audit_count == 1


def test_invalid_fake_provider_output_enters_correction_state_then_can_be_fixed(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        upload = _upload(client)
        record_id = upload.json()["data"]["record"]["id"]
        invalid = client.post(
            f"/api/v1/evidence/{record_id}/analyze",
            json={"provider_mode": "invalid_schema"},
        )
        patch = client.patch(
            f"/api/v1/evidence/{record_id}/draft",
            json={"structured_json": _valid_payload(record_id)},
        )
        reject = client.post(
            f"/api/v1/evidence/{record_id}/reject",
            json={"reason": "user rejected draft"},
        )

    invalid_body = invalid.json()
    patch_body = patch.json()
    reject_body = reject.json()
    assert invalid.status_code == 200
    assert invalid_body["data"]["ai_job"]["status"] == "failed"
    assert invalid_body["data"]["ai_job"]["error_code"] == "AI_OUTPUT_SCHEMA_INVALID"
    assert invalid_body["data"]["draft"]["status"] == "needs_correction"
    assert invalid_body["data"]["draft"]["validation_errors"]
    assert patch.status_code == 200
    assert patch_body["data"]["status"] == "draft"
    assert patch_body["data"]["validation_errors"] == []
    assert reject.status_code == 200
    assert reject_body["data"]["status"] == "rejected"

    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        failed_jobs = session.scalar(select(func.count(AIJob.id)).where(AIJob.status == "failed"))
        draft = session.scalar(
            select(EvidenceDraft).where(EvidenceDraft.evidence_record_id == record_id)
        )
        record = session.get(EvidenceRecord, record_id)

    assert failed_jobs == 1
    assert draft is not None
    assert draft.rejection_reason == "user rejected draft"
    assert record is not None
    assert record.status == "rejected"


def test_evidence_history_lists_records_with_latest_drafts(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        first_upload = _upload(client)
        first_id = first_upload.json()["data"]["record"]["id"]
        client.post(f"/api/v1/evidence/{first_id}/analyze", json={})
        second_upload = _upload(client)
        second_id = second_upload.json()["data"]["record"]["id"]
        client.post(
            f"/api/v1/evidence/{second_id}/analyze",
            json={"provider_mode": "invalid_schema"},
        )
        history = client.get(
            "/api/v1/evidence/history?limit=1",
            headers={"X-Request-ID": "evidence-history"},
        )

    body = history.json()
    assert history.status_code == 200
    assert body["meta"] == {"request_id": "evidence-history"}
    assert body["data"]["total"] == 1
    item = body["data"]["items"][0]
    assert item["record"]["id"] == second_id
    assert item["record"]["status"] == "pending"
    assert item["draft"]["evidence_record_id"] == second_id
    assert item["draft"]["status"] == "needs_correction"
    assert item["draft"]["validation_errors"]


def _upload(client: TestClient) -> Any:
    return client.post(
        "/api/v1/evidence/uploads",
        json={
            "study_date": "2026-01-05",
            "subject_id": "math",
            "files": [
                {
                    "original_name": "proof-1.png",
                    "mime_type": "image/png",
                    "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
                },
                {
                    "original_name": "proof-2.jpg",
                    "mime_type": "image/jpeg",
                    "content_base64": base64.b64encode(JPEG_BYTES).decode("ascii"),
                },
            ],
        },
    )


def _valid_payload(record_id: str) -> dict[str, Any]:
    return {
        "confirmed_facts": {"record_id": record_id, "asset_count": 2},
        "inferences": {"provider": "manual-correction"},
        "uncertain_fields": [
            {"field": "ocr_text", "reason": "manual text missing", "confidence": 0.1}
        ],
        "teaching_judgment": {
            "diagnosis": "manual_review_ready",
            "evidence_basis": ["user-edited"],
            "risk": "low",
        },
        "suggested_actions": [{"type": "confirm_or_reject", "priority": "normal"}],
    }
