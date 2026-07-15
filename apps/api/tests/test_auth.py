from collections.abc import Generator
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings

ACCESS_KEY = "test-personal-access-key-with-32-characters"
ACCESS_KEY_DIGEST = sha256(ACCESS_KEY.encode("utf-8")).hexdigest()


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", ACCESS_KEY_DIGEST)
    monkeypatch.setenv("YANTU_CORS_ALLOWED_ORIGINS", "https://study.example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_public_health_and_meta_do_not_require_access_key() -> None:
    with TestClient(create_app()) as client:
        health = client.get("/health")
        meta = client.get("/api/v1/meta")

    assert health.status_code == 200
    assert meta.status_code == 200


def test_protected_api_rejects_missing_access_key() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/auth/status",
            headers={
                "Origin": "https://study.example.com",
                "X-Request-ID": "auth-missing",
            },
        )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.headers["x-request-id"] == "auth-missing"
    assert response.headers["access-control-allow-origin"] == "https://study.example.com"
    assert response.json() == {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "A valid personal access key is required",
            "details": None,
            "request_id": "auth-missing",
        }
    }


def test_protected_api_rejects_invalid_access_key() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/auth/status",
            headers={"Authorization": "Bearer wrong-personal-access-key"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_protected_api_accepts_valid_access_key() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/auth/status",
            headers={"Authorization": f"Bearer {ACCESS_KEY}"},
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "authenticated": True,
        "mode": "personal_token",
    }


def test_production_fails_closed_without_access_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "prod"))
    monkeypatch.delenv("YANTU_AUTH_TOKEN_SHA256", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="YANTU_AUTH_TOKEN_SHA256"):
        get_settings()


@pytest.mark.parametrize("digest", ["short", "g" * 64, "a" * 63])
def test_invalid_access_key_digest_is_rejected(
    monkeypatch: pytest.MonkeyPatch, digest: str
) -> None:
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", digest)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="YANTU_AUTH_TOKEN_SHA256"):
        get_settings()
