from fastapi import APIRouter, Request

from app.cloud import require_persistent_cloud_capability
from app.data_management.service import (
    DataManagementError,
    create_backup_response,
    list_backup_responses,
    restore_backup_response,
    verify_backup_response,
)
from app.errors import ApiError
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.data_management import BackupCreateRequest, BackupListResponse, BackupResponse
from app.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["data-management"])


@router.post("/backups", response_model=ApiResponse[BackupResponse])
def create_backup_endpoint(
    request: Request,
    payload: BackupCreateRequest,
) -> ApiResponse[BackupResponse]:
    require_persistent_cloud_capability(get_settings(), "backup_restore")
    try:
        response = create_backup_response(get_settings(), label=payload.label)
    except DataManagementError as exc:
        raise _api_data_error(exc) from exc
    return api_response(response, request)


@router.get("/backups", response_model=ApiResponse[BackupListResponse])
def list_backups_endpoint(request: Request) -> ApiResponse[BackupListResponse]:
    require_persistent_cloud_capability(get_settings(), "backup_restore")
    items = list_backup_responses(get_settings())
    return api_response(BackupListResponse(items=items, total=len(items)), request)


@router.post("/backups/{backup_id}/verify", response_model=ApiResponse[BackupResponse])
def verify_backup_endpoint(request: Request, backup_id: str) -> ApiResponse[BackupResponse]:
    require_persistent_cloud_capability(get_settings(), "backup_restore")
    try:
        response = verify_backup_response(get_settings(), backup_id)
    except DataManagementError as exc:
        raise _api_data_error(exc) from exc
    return api_response(response, request)


@router.post("/backups/{backup_id}/restore", response_model=ApiResponse[BackupResponse])
def restore_backup_endpoint(request: Request, backup_id: str) -> ApiResponse[BackupResponse]:
    require_persistent_cloud_capability(get_settings(), "backup_restore")
    try:
        response = restore_backup_response(get_settings(), backup_id)
    except DataManagementError as exc:
        raise _api_data_error(exc) from exc
    return api_response(response, request)


@router.get("/exports/full", response_model=ApiResponse[BackupResponse])
def export_full_endpoint(request: Request) -> ApiResponse[BackupResponse]:
    require_persistent_cloud_capability(get_settings(), "backup_restore")
    try:
        response = create_backup_response(get_settings(), label="export")
    except DataManagementError as exc:
        raise _api_data_error(exc) from exc
    return api_response(response, request)


def _api_data_error(exc: DataManagementError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
