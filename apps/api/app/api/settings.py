from fastapi import APIRouter, Request

from app.cloud import require_persistent_cloud_capability
from app.errors import ApiError
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.settings import ProfileResponse, ProfileUpdate, RulesResponse
from app.settings import get_settings
from app.settings_api.service import SettingsApiError, read_profile, read_rules, update_profile

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/profile", response_model=ApiResponse[ProfileResponse])
def get_profile(request: Request) -> ApiResponse[ProfileResponse]:
    require_persistent_cloud_capability(get_settings(), "profile_settings")
    try:
        response = read_profile(get_settings())
    except SettingsApiError as exc:
        raise _api_settings_error(exc) from exc
    return api_response(response, request)


@router.patch("/profile", response_model=ApiResponse[ProfileResponse])
def patch_profile(
    request: Request,
    payload: ProfileUpdate,
) -> ApiResponse[ProfileResponse]:
    require_persistent_cloud_capability(get_settings(), "profile_settings")
    try:
        response = update_profile(get_settings(), payload)
    except SettingsApiError as exc:
        raise _api_settings_error(exc) from exc
    return api_response(response, request)


@router.get("/rules", response_model=ApiResponse[RulesResponse])
def get_rules(request: Request) -> ApiResponse[RulesResponse]:
    try:
        response = read_rules()
    except SettingsApiError as exc:
        raise _api_settings_error(exc) from exc
    return api_response(response, request)


def _api_settings_error(exc: SettingsApiError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
