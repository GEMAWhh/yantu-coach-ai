import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.imports.localstorage as localstorage_module
from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.imports.localstorage import (
    LOCAL_STORAGE_KEY,
    MAX_IMPORT_BYTES,
    LocalStorageImportError,
    build_localstorage_preview,
    commit_localstorage_import,
)
from app.main import create_app
from app.models.audit import AuditEvent
from app.models.import_batch import ImportBatch
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


def _prototype_payload() -> dict[str, Any]:
    return {
        "version": "1.1",
        "settings": {
            "school": "DUT",
            "major": "control",
            "subjects": "math, 841",
            "phase": "foundation",
            "examDate": "2027-12-25",
            "defaultMinutes": 245,
            "peakTime": "19:30-22:30",
            "coachStyle": "balanced",
        },
        "today": {"availableMinutes": 245, "energy": "medium", "subject": "all"},
        "tasks": [
            {
                "id": "t1",
                "subject": "math",
                "title": "closed-book recall",
                "minutes": 65,
                "priority": "must",
                "source": "weekly goal",
                "reason": "weak node",
                "standard": "80 percent correct",
                "from": "variant",
                "to": "basic",
                "knowledge": "derivative",
                "status": "todo",
            }
        ],
        "knowledge": [
            {
                "id": "k1",
                "subject": "math",
                "path": "calculus / derivative",
                "name": "derivative",
                "stage": 4,
                "recall": 76,
                "basic": 72,
                "variant": 48,
                "transfer": 20,
                "errors": 4,
                "next": "tomorrow",
            }
        ],
        "wrongs": [],
        "resources": [],
        "inbox": [],
        "goals": [],
        "records": [],
        "adjustments": [],
    }


def test_preview_accepts_prototype_json_and_reports_unknown_fields() -> None:
    payload = _prototype_payload()
    payload["legacyTopLevel"] = {"kept": True}
    payload["settings"]["legacySetting"] = "kept"
    payload["tasks"][0]["legacyTaskField"] = "kept"

    preview = build_localstorage_preview(payload)

    assert preview.source_key == LOCAL_STORAGE_KEY
    assert preview.source_version == "1.1"
    assert preview.entity_counts["tasks"] == 1
    assert preview.entity_counts["knowledge"] == 1
    assert preview.mastery_status == "imported_unverified"
    assert "legacyTopLevel" in preview.unknown_fields
    assert "settings.legacySetting" in preview.unknown_fields
    assert "tasks[0].legacyTaskField" in preview.unknown_fields
    assert preview.report["unknown_fields"] == preview.unknown_fields
    assert preview.report["mastery"]["verification"] == "imported_unverified"


def test_preview_accepts_localstorage_export_string() -> None:
    payload = _prototype_payload()
    wrapped = {LOCAL_STORAGE_KEY: json.dumps(payload)}

    preview = build_localstorage_preview(wrapped)

    assert preview.source_key == LOCAL_STORAGE_KEY
    assert preview.entity_counts["settings"] == 1


def test_missing_required_version_is_rejected() -> None:
    payload = _prototype_payload()
    del payload["version"]

    with pytest.raises(LocalStorageImportError, match="missing required field"):
        build_localstorage_preview(payload)


def test_wrong_source_key_and_corrupt_json_are_rejected() -> None:
    with pytest.raises(LocalStorageImportError, match="unsupported localStorage source key"):
        build_localstorage_preview({"key": "wrongKey", "value": json.dumps(_prototype_payload())})

    with pytest.raises(LocalStorageImportError, match="not valid JSON"):
        build_localstorage_preview("{broken-json")


def test_oversize_payload_is_rejected() -> None:
    payload = _prototype_payload()
    payload["oversize"] = "x" * (MAX_IMPORT_BYTES + 1)

    with pytest.raises(LocalStorageImportError, match="too large"):
        build_localstorage_preview(payload)


def test_duplicate_commit_is_idempotent(test_settings: RuntimeSettings) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    payload = _prototype_payload()

    with session_factory.begin() as session:
        first = commit_localstorage_import(session, payload, request_id="import-1")

    with session_factory.begin() as session:
        second = commit_localstorage_import(session, payload, request_id="import-2")

    assert first.created is True
    assert second.created is False
    assert second.batch_id == first.batch_id
    with session_factory() as session:
        batch_count = session.scalar(select(func.count(ImportBatch.id)))
        audit_count = session.scalar(select(func.count(AuditEvent.id)))
    assert batch_count == 1
    assert audit_count == 1


def test_failed_commit_rolls_back_import_batch(
    test_settings: RuntimeSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("audit failed")

    monkeypatch.setattr(localstorage_module, "write_audit_event", fail_audit)

    with pytest.raises(RuntimeError, match="audit failed"):
        with session_factory.begin() as session:
            commit_localstorage_import(session, _prototype_payload(), request_id="rollback")

    with session_factory() as session:
        batch_count = session.scalar(select(func.count(ImportBatch.id)))
        audit_count = session.scalar(select(func.count(AuditEvent.id)))
    assert batch_count == 0
    assert audit_count == 0


def test_api_preview_and_commit_use_response_envelope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    payload = _prototype_payload()

    with TestClient(create_app()) as client:
        preview_response = client.post(
            "/api/v1/imports/localstorage/preview",
            json=payload,
            headers={"X-Request-ID": "preview"},
        )
        commit_response = client.post(
            "/api/v1/imports/localstorage/commit",
            json={"source_key": LOCAL_STORAGE_KEY, "payload": payload},
            headers={"X-Request-ID": "commit"},
        )
        invalid_response = client.post(
            "/api/v1/imports/localstorage/preview",
            json={"version": ["bad"]},
            headers={"X-Request-ID": "invalid"},
        )

    assert preview_response.status_code == 200
    assert preview_response.json()["meta"] == {"request_id": "preview"}
    assert preview_response.json()["data"]["mastery_status"] == "imported_unverified"

    assert commit_response.status_code == 200
    commit_body = commit_response.json()
    assert commit_body["meta"] == {"request_id": "commit"}
    assert commit_body["data"]["created"] is True
    assert commit_body["data"]["status"] == "committed"

    assert invalid_response.status_code == 422
    assert invalid_response.json()["error"]["code"] == "LOCALSTORAGE_IMPORT_INVALID"
    assert invalid_response.json()["error"]["request_id"] == "invalid"

    get_settings.cache_clear()
