from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.migrations import initialize_database
from app.main import create_app
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


def test_profile_defaults_and_patch_are_persisted(test_settings: RuntimeSettings) -> None:
    with TestClient(create_app()) as client:
        default = client.get("/api/v1/settings/profile")
        patched = client.patch(
            "/api/v1/settings/profile",
            json={
                "name": "hvv",
                "target_school": "DUT",
                "target_major": "control",
                "exam_date": "2026-12-20",
                "current_phase": "强化",
                "coach_style": "strict",
                "timezone": "Asia/Shanghai",
            },
        )
        reloaded = client.get("/api/v1/settings/profile")

    assert default.status_code == 200
    assert default.json()["data"]["target_school"] == "大连理工大学"
    assert (test_settings.data_root / "settings" / "profile.json").is_file()
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "hvv"
    assert patched.json()["data"]["exam_date"] == "2026-12-20"
    assert reloaded.status_code == 200
    assert reloaded.json()["data"] == patched.json()["data"]


def test_rules_endpoint_returns_governed_rule_files(test_settings: RuntimeSettings) -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/settings/rules")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    keys = {item["key"] for item in data["items"]}
    assert keys == {"mastery", "planning", "quality_gates"}
    for item in data["items"]:
        assert item["path"].startswith("config/")
        assert ":" not in item["path"]
        assert len(item["sha256"]) == 64
        assert item["content"]
    versions = {item["key"]: item["version"] for item in data["items"]}
    assert versions["mastery"] == "mastery-v1.0.0"
    assert versions["planning"] == "planning-v1.0.0"
    assert versions["quality_gates"] == "quality-gates-v1"
