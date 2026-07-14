from pathlib import Path, PurePath

from app.files.backup import (
    BackupManifest,
    BackupResult,
    create_backup,
    restore_backup,
    verify_backup,
)
from app.files.exceptions import BackupIntegrityError
from app.schemas.data_management import BackupManifestResponse, BackupResponse
from app.settings import RuntimeSettings


class DataManagementError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def create_backup_response(settings: RuntimeSettings, *, label: str) -> BackupResponse:
    _validate_label(label)
    return _response_from_result(create_backup(settings, label=label))


def list_backup_responses(settings: RuntimeSettings) -> list[BackupResponse]:
    settings.ensure_runtime_dirs()
    backups = sorted(settings.backups_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime)
    return [_response_from_path(path) for path in reversed(backups)]


def verify_backup_response(settings: RuntimeSettings, backup_id: str) -> BackupResponse:
    path = _backup_path(settings, backup_id)
    try:
        manifest = verify_backup(path)
    except BackupIntegrityError as exc:
        raise DataManagementError(
            str(exc),
            code="BACKUP_VERIFICATION_FAILED",
            status_code=422,
            details={"backup_id": backup_id},
        ) from exc
    return _response_from_path(path, manifest=manifest)


def restore_backup_response(settings: RuntimeSettings, backup_id: str) -> BackupResponse:
    path = _backup_path(settings, backup_id)
    try:
        result = restore_backup(settings, path)
    except BackupIntegrityError as exc:
        raise DataManagementError(
            str(exc),
            code="BACKUP_VERIFICATION_FAILED",
            status_code=422,
            details={"backup_id": backup_id},
        ) from exc
    return _response_from_result(result)


def _backup_path(settings: RuntimeSettings, backup_id: str) -> Path:
    if not backup_id or PurePath(backup_id).name != backup_id or "\\" in backup_id:
        raise DataManagementError(
            "backup id must be a backup file name",
            code="BACKUP_ID_INVALID",
            status_code=422,
            details={"backup_id": backup_id},
        )
    path = (settings.backups_dir / backup_id).resolve()
    backups_dir = settings.backups_dir.resolve()
    if path.parent != backups_dir or path.suffix != ".zip":
        raise DataManagementError(
            "backup id must be a backup zip file name",
            code="BACKUP_ID_INVALID",
            status_code=422,
            details={"backup_id": backup_id},
        )
    if not path.is_file():
        raise DataManagementError(
            "backup not found",
            code="BACKUP_NOT_FOUND",
            status_code=404,
            details={"backup_id": backup_id},
        )
    return path


def _validate_label(label: str) -> None:
    if not label.replace("-", "").replace("_", "").isalnum():
        raise DataManagementError(
            "backup label may contain only letters, digits, hyphen, and underscore",
            code="BACKUP_LABEL_INVALID",
            status_code=422,
            details={"label": label},
        )


def _response_from_result(result: BackupResult) -> BackupResponse:
    return _response_from_path(
        result.path,
        manifest=result.manifest,
        pre_restore_backup_id=result.pre_restore_backup.name if result.pre_restore_backup else None,
    )


def _response_from_path(
    path: Path,
    *,
    manifest: BackupManifest | None = None,
    pre_restore_backup_id: str | None = None,
) -> BackupResponse:
    stat = path.stat()
    return BackupResponse(
        backup_id=path.name,
        size_bytes=stat.st_size,
        created_at=datetime_from_timestamp(stat.st_mtime),
        manifest=BackupManifestResponse.from_manifest(manifest) if manifest is not None else None,
        pre_restore_backup_id=pre_restore_backup_id,
    )


def datetime_from_timestamp(timestamp: float):
    from datetime import UTC, datetime

    return datetime.fromtimestamp(timestamp, tz=UTC)
