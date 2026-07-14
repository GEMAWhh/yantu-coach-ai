import base64
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.migrations import initialize_database
from app.main import create_app
from app.settings import RuntimeSettings, get_settings

PNG_BYTES = b"\x89PNG\r\n\x1a\ndata-management-backup"


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


def test_backup_verify_restore_and_export_round_trip(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        upload = _upload_png(client)
        asset_id = upload.json()["data"]["id"]
        backup = client.post("/api/v1/backups", json={"label": "api_test"})
        backup_id = backup.json()["data"]["backup_id"]
        listed = client.get("/api/v1/backups")
        verified = client.post(f"/api/v1/backups/{backup_id}/verify")
        deleted = client.delete(f"/api/v1/assets/{asset_id}")
        hidden = client.get(f"/api/v1/assets/{asset_id}/metadata")
        restored = client.post(f"/api/v1/backups/{backup_id}/restore")
        metadata = client.get(f"/api/v1/assets/{asset_id}/metadata")
        content = client.get(f"/api/v1/assets/{asset_id}/content")
        exported = client.get("/api/v1/exports/full")

    assert upload.status_code == 200
    assert backup.status_code == 200
    assert backup_id.endswith(".zip")
    assert backup.json()["data"]["manifest"]["database"]["path"] == "database/study.db"
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert verified.status_code == 200
    assert verified.json()["data"]["manifest"]["manifest_hash"]
    assert deleted.status_code == 200
    assert hidden.status_code == 404
    assert restored.status_code == 200
    assert restored.json()["data"]["pre_restore_backup_id"].endswith(".zip")
    assert metadata.status_code == 200
    assert metadata.json()["data"]["state"] == "inbox"
    assert content.status_code == 200
    assert base64.b64decode(content.json()["data"]["content_base64"]) == PNG_BYTES
    assert exported.status_code == 200
    assert exported.json()["data"]["backup_id"].startswith("export-")
    assert (test_settings.backups_dir / exported.json()["data"]["backup_id"]).is_file()


def test_backup_api_rejects_invalid_label_and_missing_backup(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        invalid = client.post("/api/v1/backups", json={"label": "../bad"})
        missing = client.post("/api/v1/backups/missing.zip/verify")

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "BACKUP_LABEL_INVALID"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BACKUP_NOT_FOUND"


def _upload_png(client: TestClient) -> Any:
    return client.post(
        "/api/v1/assets",
        json={
            "original_name": "backup-proof.png",
            "mime_type": "image/png",
            "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
        },
    )
