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
from app.models.asset import Asset
from app.settings import (
    DatabaseBackend,
    RuntimeSettings,
    SupabaseStorageSettings,
    get_settings,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\nasset-api-test-png"
PDF_BYTES = b"%PDF-1.7\nasset-api-test-pdf"


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


def test_asset_upload_deduplicates_and_reads_content(test_settings: RuntimeSettings) -> None:
    with TestClient(create_app()) as client:
        first = _upload_png(client)
        second = _upload_png(client)
        asset_id = first.json()["data"]["id"]
        metadata = client.get(f"/api/v1/assets/{asset_id}/metadata")
        content = client.get(f"/api/v1/assets/{asset_id}/content")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["id"] == asset_id
    assert second.json()["data"]["reference_count"] == 2
    assert metadata.status_code == 200
    assert metadata.json()["data"]["storage_path"].startswith("files/original/")
    assert ":" not in metadata.json()["data"]["storage_path"]
    assert content.status_code == 200
    assert base64.b64decode(content.json()["data"]["content_base64"]) == PNG_BYTES
    assert (test_settings.data_root / metadata.json()["data"]["storage_path"]).is_file()


def test_asset_delete_restore_and_resource_index(test_settings: RuntimeSettings) -> None:
    with TestClient(create_app()) as client:
        upload = _upload_png(client)
        asset_id = upload.json()["data"]["id"]
        empty_resources = client.get("/api/v1/resources")
        resource = client.post("/api/v1/resources", json={"asset_id": asset_id})
        resources = client.get("/api/v1/resources")
        deleted = client.delete(f"/api/v1/assets/{asset_id}")
        hidden = client.get(f"/api/v1/assets/{asset_id}/metadata")
        restored = client.post(f"/api/v1/assets/{asset_id}/restore")
        content = client.get(f"/api/v1/assets/{asset_id}/content")

    assert empty_resources.status_code == 200
    assert empty_resources.json()["data"]["total"] == 0
    assert resource.status_code == 200
    assert resource.json()["data"]["resource_type"] == "asset"
    assert resource.json()["data"]["asset"]["state"] == "organized"
    assert resources.status_code == 200
    assert resources.json()["data"]["total"] == 1
    assert deleted.status_code == 200
    assert deleted.json()["data"]["state"] == "deleted"
    assert hidden.status_code == 404
    assert hidden.json()["error"]["code"] == "ASSET_NOT_FOUND"
    assert restored.status_code == 200
    assert restored.json()["data"]["state"] == "inbox"
    assert content.status_code == 200


def test_asset_upload_rejects_masquerade_and_path_traversal(
    test_settings: RuntimeSettings,
) -> None:
    with TestClient(create_app()) as client:
        masquerade = client.post(
            "/api/v1/assets",
            json={
                "original_name": "fake.png",
                "mime_type": "image/png",
                "content_base64": base64.b64encode(PDF_BYTES).decode("ascii"),
            },
        )
        traversal = client.post(
            "/api/v1/assets",
            json={
                "original_name": "../proof.png",
                "mime_type": "image/png",
                "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            },
        )

    assert masquerade.status_code == 422
    assert masquerade.json()["error"]["code"] == "ASSET_TYPE_INVALID"
    assert traversal.status_code == 422
    assert traversal.json()["error"]["code"] == "ASSET_NAME_INVALID"


def test_cloud_storage_failure_returns_503_and_rolls_back_asset_metadata(
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

    monkeypatch.setattr("app.api.assets.get_settings", lambda: cloud_settings)
    monkeypatch.setattr("app.files.storage.SupabaseObjectStorage.upload", fail_upload)

    with TestClient(create_app()) as client:
        response = _upload_png(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CLOUD_FILE_STORAGE_UNAVAILABLE"
    assert "example.supabase.co" not in str(response.json())
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory() as session:
        assert session.scalar(select(func.count(Asset.id))) == 0


def _upload_png(client: TestClient) -> Any:
    return client.post(
        "/api/v1/assets",
        json={
            "original_name": "proof.png",
            "mime_type": "image/png",
            "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
        },
    )
