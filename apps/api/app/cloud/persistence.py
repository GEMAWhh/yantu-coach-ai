from typing import Literal

from app.errors import ApiError
from app.settings import DatabaseBackend, RuntimeSettings

CloudCapability = Literal["asset_storage", "backup_restore", "profile_settings"]

_CAPABILITY_ERRORS: dict[CloudCapability, tuple[str, str]] = {
    "asset_storage": (
        "CLOUD_FILE_STORAGE_NOT_READY",
        "Cloud file storage is not configured yet",
    ),
    "backup_restore": (
        "CLOUD_BACKUP_NOT_READY",
        "Cloud backup and restore are not configured yet",
    ),
    "profile_settings": (
        "CLOUD_SETTINGS_NOT_READY",
        "Cloud profile settings persistence is not configured yet",
    ),
}


def require_persistent_cloud_capability(
    settings: RuntimeSettings,
    capability: CloudCapability,
) -> None:
    if settings.database_backend is not DatabaseBackend.POSTGRESQL:
        return
    code, message = _CAPABILITY_ERRORS[capability]
    raise ApiError(
        status_code=503,
        code=code,
        message=message,
        details={
            "capability": capability,
            "next_action": (
                "Configure the matching persistent cloud service before using " "this endpoint."
            ),
        },
    )
