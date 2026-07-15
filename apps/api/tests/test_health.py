from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_health_uses_isolated_test_data_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_root = tmp_path / "data" / "test"
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(data_root))

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "ok",
            "service": "yantu-coach-api",
            "environment": "test",
            "data_root": "data/test",
        },
        "meta": {"request_id": response.headers["x-request-id"]},
    }
    assert (data_root / "database").is_dir()
    assert (data_root / "database" / "study.db").is_file()
    assert (data_root / "files" / "original").is_dir()
    assert not (tmp_path / "data" / "prod").exists()


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "staging")

    with pytest.raises(ValueError, match="YANTU_APP_ENV"):
        get_settings()


def test_configured_frontend_origin_can_use_api(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    monkeypatch.setenv("YANTU_CORS_ALLOWED_ORIGINS", "https://study.example.com")

    with TestClient(create_app()) as client:
        response = client.options(
            "/api/v1/meta",
            headers={
                "Origin": "https://study.example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,X-Request-ID",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://study.example.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_untrusted_frontend_origin_is_not_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    monkeypatch.setenv("YANTU_CORS_ALLOWED_ORIGINS", "https://study.example.com")

    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/meta",
            headers={"Origin": "https://attacker.example.com"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize(
    "configured_origins",
    ["*", "https://study.example.com/path", "javascript:alert(1)"],
)
def test_unsafe_cors_origins_are_rejected(
    monkeypatch: pytest.MonkeyPatch, configured_origins: str
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_CORS_ALLOWED_ORIGINS", configured_origins)
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", "a" * 64)

    with pytest.raises(ValueError, match="YANTU_CORS_ALLOWED_ORIGINS"):
        get_settings()
