import json

import httpx
import pytest

from app.files.exceptions import (
    PersistentStorageError,
    RemoteObjectNotFoundError,
    UnsafeFileNameError,
)
from app.files.object_storage import SupabaseObjectStorage
from app.settings import SupabaseStorageSettings

FAKE_SECRET = "fake-secret-key-with-at-least-32-characters"
PNG_BYTES = b"\x89PNG\r\n\x1a\nremote-storage"


def _settings() -> SupabaseStorageSettings:
    return SupabaseStorageSettings(
        project_url="https://example.supabase.co",
        secret_key=FAKE_SECRET,
        bucket="yantu-assets",
    )


def test_private_storage_upload_download_and_delete_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=PNG_BYTES)
        return httpx.Response(200, json={"message": "ok"})

    storage = SupabaseObjectStorage(_settings(), transport=httpx.MockTransport(handler))
    object_path = "files/original/ab/abcdef.png"

    storage.upload(object_path, PNG_BYTES, "image/png")
    downloaded = storage.download(object_path)
    storage.delete(object_path)

    assert downloaded == PNG_BYTES
    assert [request.method for request in requests] == ["POST", "GET", "DELETE"]
    assert requests[0].url.path == f"/storage/v1/object/yantu-assets/{object_path}"
    assert requests[0].headers["content-type"] == "image/png"
    assert requests[0].headers["x-upsert"] == "true"
    assert requests[1].url.path == (f"/storage/v1/object/authenticated/yantu-assets/{object_path}")
    assert json.loads(requests[2].content) == {"prefixes": [object_path]}
    assert all(request.headers["apikey"] == FAKE_SECRET for request in requests)
    assert all(request.headers["authorization"] == f"Bearer {FAKE_SECRET}" for request in requests)


def test_storage_failure_is_sanitized() -> None:
    storage = SupabaseObjectStorage(
        _settings(),
        transport=httpx.MockTransport(lambda _request: httpx.Response(500)),
    )

    with pytest.raises(PersistentStorageError) as error:
        storage.upload("files/original/ab/abcdef.png", PNG_BYTES, "image/png")

    assert FAKE_SECRET not in str(error.value)
    assert "example.supabase.co" not in str(error.value)


def test_missing_remote_object_has_distinct_error() -> None:
    storage = SupabaseObjectStorage(
        _settings(),
        transport=httpx.MockTransport(lambda _request: httpx.Response(404)),
    )

    with pytest.raises(RemoteObjectNotFoundError, match="cloud object is missing"):
        storage.download("files/original/ab/missing.png")


def test_storage_rejects_non_server_generated_paths() -> None:
    storage = SupabaseObjectStorage(
        _settings(),
        transport=httpx.MockTransport(lambda _request: httpx.Response(200)),
    )

    with pytest.raises(UnsafeFileNameError, match="path"):
        storage.upload("../outside.png", PNG_BYTES, "image/png")
