import base64
import importlib
from collections.abc import Generator
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.cloud import require_persistent_cloud_capability
from app.errors import ApiError
from app.settings import get_settings

ACCESS_KEY = "cloud-test-access-key-with-at-least-32-characters"
PNG_BYTES = b"\x89PNG\r\n\x1a\ncloud-guard"


@pytest.fixture
def cloud_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[TestClient, None, None]:
    main_module = importlib.import_module("app.main")
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", sha256(ACCESS_KEY.encode("utf-8")).hexdigest())
    monkeypatch.setenv(
        "YANTU_DATABASE_URL",
        "postgresql://postgres:password@db.example.com:5432/postgres?sslmode=require",
    )
    monkeypatch.setattr(main_module, "initialize_database", lambda _settings: None)
    get_settings.cache_clear()
    with TestClient(main_module.create_app()) as client:
        yield client
    get_settings.cache_clear()


def _request_kwargs() -> dict[str, Any]:
    return {"headers": {"Authorization": f"Bearer {ACCESS_KEY}"}}


@pytest.mark.parametrize(
    "method,path,payload,expected_code",
    [
        (
            "post",
            "/api/v1/assets",
            {
                "original_name": "proof.png",
                "mime_type": "image/png",
                "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            },
            "CLOUD_FILE_STORAGE_NOT_READY",
        ),
        ("get", "/api/v1/assets/asset-1/content", None, "CLOUD_FILE_STORAGE_NOT_READY"),
        (
            "post",
            "/api/v1/evidence/uploads",
            {
                "study_date": "2026-09-21",
                "subject_id": "math",
                "files": [
                    {
                        "original_name": "proof.png",
                        "mime_type": "image/png",
                        "content_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
                    }
                ],
            },
            "CLOUD_FILE_STORAGE_NOT_READY",
        ),
        ("post", "/api/v1/backups", {"label": "manual"}, "CLOUD_BACKUP_NOT_READY"),
        ("get", "/api/v1/backups", None, "CLOUD_BACKUP_NOT_READY"),
        ("post", "/api/v1/backups/example.zip/verify", None, "CLOUD_BACKUP_NOT_READY"),
        ("post", "/api/v1/backups/example.zip/restore", None, "CLOUD_BACKUP_NOT_READY"),
        ("get", "/api/v1/exports/full", None, "CLOUD_BACKUP_NOT_READY"),
        ("get", "/api/v1/settings/profile", None, "CLOUD_SETTINGS_NOT_READY"),
        ("patch", "/api/v1/settings/profile", {"name": "cloud user"}, "CLOUD_SETTINGS_NOT_READY"),
    ],
)
def test_cloud_runtime_rejects_ephemeral_filesystem_features(
    cloud_client: TestClient,
    method: str,
    path: str,
    payload: dict[str, object] | None,
    expected_code: str,
) -> None:
    request_kwargs = _request_kwargs()
    if payload is not None:
        request_kwargs["json"] = payload

    response = getattr(cloud_client, method)(path, **request_kwargs)

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == expected_code
    assert error["details"]["next_action"]
    assert "password" not in str(error)
    assert "runtime" not in str(error)


def test_cloud_runtime_keeps_rule_reads_available(cloud_client: TestClient) -> None:
    response = cloud_client.get("/api/v1/settings/rules", **_request_kwargs())

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3


def test_configured_supabase_storage_opens_only_asset_capability(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", sha256(ACCESS_KEY.encode("utf-8")).hexdigest())
    monkeypatch.setenv(
        "YANTU_DATABASE_URL",
        "postgresql://postgres:password@db.example.com:5432/postgres?sslmode=require",
    )
    monkeypatch.setenv("YANTU_SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("YANTU_SUPABASE_SECRET_KEY", "fake-secret-key-with-at-least-32-characters")
    monkeypatch.setenv("YANTU_SUPABASE_STORAGE_BUCKET", "yantu-assets")
    get_settings.cache_clear()
    settings = get_settings()

    require_persistent_cloud_capability(settings, "asset_storage")
    with pytest.raises(ApiError) as backup_error:
        require_persistent_cloud_capability(settings, "backup_restore")

    assert getattr(backup_error.value, "code", None) == "CLOUD_BACKUP_NOT_READY"
    get_settings.cache_clear()
