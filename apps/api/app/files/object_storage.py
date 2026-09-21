from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

import httpx

from app.files.exceptions import (
    PersistentStorageError,
    RemoteObjectNotFoundError,
    UnsafeFileNameError,
)
from app.settings import SupabaseStorageSettings

REQUEST_TIMEOUT_SECONDS = 30.0


class SupabaseObjectStorage:
    def __init__(
        self,
        settings: SupabaseStorageSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    def upload(self, object_path: str, content: bytes, mime_type: str) -> None:
        response = self._request(
            "POST",
            self._object_url(object_path),
            content=content,
            headers={
                "cache-control": "max-age=3600",
                "content-type": mime_type,
                "x-upsert": "true",
            },
        )
        self._raise_for_status(response, operation="upload")

    def download(self, object_path: str) -> bytes:
        response = self._request(
            "GET",
            self._object_url(object_path, authenticated=True),
        )
        if response.status_code == 404:
            raise RemoteObjectNotFoundError("cloud object is missing")
        self._raise_for_status(response, operation="download")
        return response.content

    def delete(self, object_path: str) -> None:
        safe_path = _safe_object_path(object_path)
        bucket = quote(self._settings.bucket, safe="")
        response = self._request(
            "DELETE",
            f"{self._storage_url}/object/{bucket}",
            json={"prefixes": [safe_path]},
        )
        self._raise_for_status(response, operation="delete")

    @property
    def _storage_url(self) -> str:
        return f"{self._settings.project_url}/storage/v1"

    def _object_url(self, object_path: str, *, authenticated: bool = False) -> str:
        safe_path = quote(_safe_object_path(object_path), safe="/")
        bucket = quote(self._settings.bucket, safe="")
        route = "object/authenticated" if authenticated else "object"
        return f"{self._storage_url}/{route}/{bucket}/{safe_path}"

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        headers = {
            "apikey": self._settings.secret_key,
            "authorization": f"Bearer {self._settings.secret_key}",
        }
        extra_headers = kwargs.pop("headers", None)
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})
        try:
            with httpx.Client(
                timeout=REQUEST_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                return client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise PersistentStorageError("cloud object storage request failed") from exc

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, operation: str) -> None:
        if response.is_success:
            return
        raise PersistentStorageError(f"cloud object storage {operation} failed")


def _safe_object_path(object_path: str) -> str:
    if not object_path or "\\" in object_path or object_path.startswith("/"):
        raise UnsafeFileNameError("cloud object path is invalid")
    path = PurePosixPath(object_path)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafeFileNameError("cloud object path is invalid")
    return path.as_posix()
