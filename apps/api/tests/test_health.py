from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.migrations import use_batch_migrations
from app.main import create_app
from app.settings import DatabaseBackend, get_settings


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


def test_production_requires_a_postgresql_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", "a" * 64)
    monkeypatch.delenv("YANTU_DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="YANTU_DATABASE_URL is required"):
        get_settings()


@pytest.mark.parametrize(
    "database_url, message",
    [
        ("sqlite:////tmp/study.db", "production must use a PostgreSQL"),
        ("postgresql://user:password@db.example.com:5432/study", "must require TLS"),
    ],
)
def test_production_rejects_unsafe_database_urls(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    message: str,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", "a" * 64)
    monkeypatch.setenv("YANTU_DATABASE_URL", database_url)

    with pytest.raises((RuntimeError, ValueError), match=message):
        get_settings()


def test_production_normalizes_tls_postgresql_url_without_exposing_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "prod")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("YANTU_AUTH_TOKEN_SHA256", "a" * 64)
    monkeypatch.setenv(
        "YANTU_DATABASE_URL",
        "postgresql://postgres:example-password@db.example.com:5432/postgres?sslmode=require",
    )

    settings = get_settings()

    assert settings.database_backend is DatabaseBackend.POSTGRESQL
    assert settings.database_url == (
        "postgresql+psycopg://postgres:example-password@db.example.com:5432/postgres?sslmode=require"
    )
    assert use_batch_migrations(settings) is False
    settings.ensure_runtime_dirs()
    assert not settings.database_dir.exists()


def test_test_environment_rejects_cloud_postgresql_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv(
        "YANTU_DATABASE_URL",
        "postgresql://postgres:example-password@db.example.com:5432/postgres?sslmode=require",
    )

    with pytest.raises(RuntimeError, match="dev/test runtime"):
        get_settings()
