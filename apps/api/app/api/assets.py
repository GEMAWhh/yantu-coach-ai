from fastapi import APIRouter, Request
from sqlalchemy.orm import Session, sessionmaker

from app.assets.service import (
    AssetServiceError,
    api_error_from_storage_error,
    create_asset,
    create_resource_from_asset,
    delete_asset,
    get_asset,
    list_resources,
    read_asset_content,
    restore_asset,
)
from app.cloud import require_persistent_cloud_capability
from app.db.database import get_session_factory
from app.errors import ApiError
from app.files.exceptions import (
    FileReferenceError,
    PersistentStorageError,
    UnsafeFileNameError,
    UnsupportedFileTypeError,
)
from app.responses import api_response
from app.schemas.assets import (
    AssetContentResponse,
    AssetResponse,
    AssetUploadRequest,
    ResourceCreate,
    ResourceListResponse,
    ResourceResponse,
)
from app.schemas.common import ApiResponse
from app.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["assets"])


@router.post("/assets", response_model=ApiResponse[AssetResponse])
def upload_asset(
    request: Request,
    payload: AssetUploadRequest,
) -> ApiResponse[AssetResponse]:
    settings = get_settings()
    require_persistent_cloud_capability(settings, "asset_storage")
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            asset = create_asset(settings, session, **payload.model_dump())
            response = AssetResponse.from_model(asset)
    except (
        FileReferenceError,
        PersistentStorageError,
        UnsafeFileNameError,
        UnsupportedFileTypeError,
    ) as exc:
        raise _api_asset_error(api_error_from_storage_error(exc)) from exc
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.get("/assets/{asset_id}/metadata", response_model=ApiResponse[AssetResponse])
def asset_metadata(request: Request, asset_id: str) -> ApiResponse[AssetResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = AssetResponse.from_model(get_asset(session, asset_id))
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.get("/assets/{asset_id}/content", response_model=ApiResponse[AssetContentResponse])
def asset_content(request: Request, asset_id: str) -> ApiResponse[AssetContentResponse]:
    settings = get_settings()
    require_persistent_cloud_capability(settings, "asset_storage")
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            content = read_asset_content(settings, session, asset_id)
            response = AssetContentResponse(
                metadata=AssetResponse.from_model(content.asset),
                content_base64=content.content_base64,
            )
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.delete("/assets/{asset_id}", response_model=ApiResponse[AssetResponse])
def delete_asset_endpoint(request: Request, asset_id: str) -> ApiResponse[AssetResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            response = AssetResponse.from_model(delete_asset(session, asset_id))
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.post("/assets/{asset_id}/restore", response_model=ApiResponse[AssetResponse])
def restore_asset_endpoint(request: Request, asset_id: str) -> ApiResponse[AssetResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            response = AssetResponse.from_model(restore_asset(session, asset_id))
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.post("/resources", response_model=ApiResponse[ResourceResponse])
def create_resource(
    request: Request,
    payload: ResourceCreate,
) -> ApiResponse[ResourceResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            response = ResourceResponse.from_asset(
                create_resource_from_asset(session, payload.asset_id)
            )
    except AssetServiceError as exc:
        raise _api_asset_error(exc) from exc
    return api_response(response, request)


@router.get("/resources", response_model=ApiResponse[ResourceListResponse])
def resources(request: Request) -> ApiResponse[ResourceListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [ResourceResponse.from_asset(asset) for asset in list_resources(session)]
    return api_response(ResourceListResponse(items=items, total=len(items)), request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_asset_error(exc: AssetServiceError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
