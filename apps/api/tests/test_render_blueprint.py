from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
SITES_ORIGIN = "https://yantu-coach-ai-demo-20260715.h1660930192.chatgpt.site"
PRIVATE_ENV_KEYS = {
    "YANTU_DATABASE_URL",
    "YANTU_AUTH_TOKEN_SHA256",
    "YANTU_SUPABASE_URL",
    "YANTU_SUPABASE_SECRET_KEY",
}


def test_render_blueprint_defines_guarded_free_api_service() -> None:
    payload: dict[str, Any] = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))

    assert len(payload["services"]) == 1
    service = payload["services"][0]
    assert service["type"] == "web"
    assert service["name"] == "yantu-coach-api"
    assert service["runtime"] == "python"
    assert service["plan"] == "free"
    assert service["branch"] == "develop"
    assert service["autoDeployTrigger"] == "checksPass"
    assert service["buildCommand"] == "pip install -e apps/api"
    expected_start_command = " ".join(
        [
            "python -m uvicorn app.main:app",
            "--app-dir apps/api",
            "--host 0.0.0.0",
            "--port $PORT",
        ]
    )
    assert service["startCommand"] == expected_start_command
    assert service["healthCheckPath"] == "/health"
    assert "preDeployCommand" not in service

    env_vars = {item["key"]: item for item in service["envVars"]}
    assert env_vars["PYTHON_VERSION"]["value"] == "3.12.14"
    assert env_vars["YANTU_APP_ENV"]["value"] == "prod"
    assert env_vars["YANTU_CORS_ALLOWED_ORIGINS"]["value"] == SITES_ORIGIN
    assert env_vars["YANTU_SUPABASE_STORAGE_BUCKET"]["value"] == "yantu-assets"
    for key in PRIVATE_ENV_KEYS:
        assert env_vars[key] == {"key": key, "sync": False}
