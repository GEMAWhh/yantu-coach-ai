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
    assert (data_root / "files" / "original").is_dir()
    assert not (tmp_path / "data" / "prod").exists()


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "staging")

    with pytest.raises(ValueError, match="YANTU_APP_ENV"):
        get_settings()
