from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Body, Request

from app.db.database import get_session_factory
from app.errors import ApiError
from app.imports.localstorage import (
    LocalStorageImportError,
    build_localstorage_preview,
    commit_localstorage_import,
)
from app.request_context import get_request_id
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.imports import (
    LocalStorageImportCommitResponse,
    LocalStorageImportPreviewResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])
JsonBody = Annotated[Any, Body(description="Prototype localStorage JSON export")]


@router.post(
    "/localstorage/preview",
    response_model=ApiResponse[LocalStorageImportPreviewResponse],
)
def preview_localstorage_import(
    request: Request,
    payload: JsonBody,
) -> ApiResponse[LocalStorageImportPreviewResponse]:
    try:
        preview = build_localstorage_preview(payload)
    except LocalStorageImportError as exc:
        raise _api_import_error(exc) from exc
    return api_response(LocalStorageImportPreviewResponse.from_preview(preview), request)


@router.post(
    "/localstorage/commit",
    response_model=ApiResponse[LocalStorageImportCommitResponse],
)
def commit_localstorage_import_endpoint(
    request: Request,
    payload: JsonBody,
) -> ApiResponse[LocalStorageImportCommitResponse]:
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    try:
        with session_factory.begin() as session:
            result = commit_localstorage_import(
                session,
                payload,
                request_id=get_request_id(request),
            )
    except LocalStorageImportError as exc:
        raise _api_import_error(exc) from exc
    return api_response(LocalStorageImportCommitResponse.from_commit_result(result), request)


def _api_import_error(exc: LocalStorageImportError) -> ApiError:
    return ApiError(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="LOCALSTORAGE_IMPORT_INVALID",
        message=str(exc),
        details=exc.details,
    )
