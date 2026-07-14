from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _assert_error_shape(
    response_json: dict[str, Any],
    *,
    code: str,
    request_id: str,
) -> None:
    assert set(response_json) == {"error"}
    assert response_json["error"]["code"] == code
    assert response_json["error"]["request_id"] == request_id
    assert isinstance(response_json["error"]["message"], str)


def test_meta_uses_unified_response_and_request_id() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/meta", headers={"X-Request-ID": "contract-meta"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "contract-meta"
    assert response.json()["meta"] == {"request_id": "contract-meta"}
    assert response.json()["data"]["contract_version"] == "contract-v1"


def test_openapi_exposes_contract_schema() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/meta" in schema["paths"]
    assert "ApiErrorResponse" in schema["components"]["schemas"]


def test_validation_error_uses_unified_error_response() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/meta?include_features=not-bool",
            headers={"X-Request-ID": "contract-422"},
        )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "contract-422"
    body = response.json()
    _assert_error_shape(body, code="VALIDATION_ERROR", request_id="contract-422")
    assert "errors" in body["error"]["details"]


def test_not_found_uses_unified_error_response() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/missing", headers={"X-Request-ID": "contract-404"})

    assert response.status_code == 404
    assert response.headers["x-request-id"] == "contract-404"
    _assert_error_shape(response.json(), code="NOT_FOUND", request_id="contract-404")


def test_version_conflict_uses_unified_error_response() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/meta/version-check",
            headers={"X-Request-ID": "contract-409", "If-Match": "old-contract"},
        )

    assert response.status_code == 409
    assert response.headers["x-request-id"] == "contract-409"
    body = response.json()
    _assert_error_shape(body, code="VERSION_CONFLICT", request_id="contract-409")
    assert body["error"]["details"] == {
        "expected": "contract-v1",
        "received": "old-contract",
    }


def test_unhandled_error_uses_unified_error_response() -> None:
    app = create_app()

    @app.get("/api/v1/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/boom", headers={"X-Request-ID": "contract-500"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "contract-500"
    _assert_error_shape(response.json(), code="INTERNAL_SERVER_ERROR", request_id="contract-500")
