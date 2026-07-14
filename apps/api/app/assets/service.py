import base64
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.files.exceptions import FileReferenceError, UnsafeFileNameError, UnsupportedFileTypeError
from app.files.storage import store_original_file
from app.models.asset import Asset
from app.settings import RuntimeSettings

ASSET_RESOURCE_STATES = {"organized", "archived"}


@dataclass(frozen=True)
class AssetContent:
    asset: Asset
    content_base64: str


class AssetServiceError(ValueError):
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


def create_asset(
    settings: RuntimeSettings,
    session: Session,
    *,
    original_name: str,
    mime_type: str,
    content_base64: str,
    state: str = "inbox",
) -> Asset:
    if state == "deleted":
        raise AssetServiceError(
            "asset upload cannot start in deleted state",
            code="ASSET_STATE_INVALID",
            status_code=422,
            details={"state": state},
        )
    data = _decode_base64(content_base64)
    settings.ensure_runtime_dirs()
    temp_dir = settings.cache_dir / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid4()}.upload"
    temp_path.write_bytes(data)
    try:
        asset = store_original_file(
            settings,
            session,
            source_path=temp_path,
            original_name=original_name,
            declared_mime_type=mime_type,
            state=state,
        )
        session.flush()
        return asset
    finally:
        temp_path.unlink(missing_ok=True)


def get_asset(session: Session, asset_id: str, *, include_deleted: bool = False) -> Asset:
    asset = session.get(Asset, asset_id)
    if asset is None or (asset.state == "deleted" and not include_deleted):
        raise AssetServiceError(
            "asset not found",
            code="ASSET_NOT_FOUND",
            status_code=404,
            details={"asset_id": asset_id},
        )
    return asset


def read_asset_content(settings: RuntimeSettings, session: Session, asset_id: str) -> AssetContent:
    asset = get_asset(session, asset_id)
    path = _asset_file_path(settings, asset)
    if not path.is_file():
        raise AssetServiceError(
            "asset file is missing",
            code="ASSET_FILE_MISSING",
            status_code=404,
            details={"asset_id": asset_id},
        )
    return AssetContent(
        asset=asset,
        content_base64=base64.b64encode(path.read_bytes()).decode("ascii"),
    )


def delete_asset(session: Session, asset_id: str) -> Asset:
    asset = get_asset(session, asset_id, include_deleted=True)
    asset.state = "deleted"
    session.flush()
    return asset


def restore_asset(session: Session, asset_id: str) -> Asset:
    asset = get_asset(session, asset_id, include_deleted=True)
    if asset.state == "deleted":
        asset.state = "inbox"
    session.flush()
    return asset


def create_resource_from_asset(session: Session, asset_id: str) -> Asset:
    asset = get_asset(session, asset_id)
    if asset.state == "inbox":
        asset.state = "organized"
    session.flush()
    return asset


def list_resources(session: Session) -> list[Asset]:
    return list(
        session.scalars(
            select(Asset)
            .where(Asset.state.in_(ASSET_RESOURCE_STATES))
            .order_by(Asset.updated_at.desc(), Asset.id)
        ).all()
    )


def api_error_from_storage_error(
    exc: FileReferenceError | UnsafeFileNameError | UnsupportedFileTypeError,
) -> AssetServiceError:
    if isinstance(exc, UnsupportedFileTypeError):
        return AssetServiceError(str(exc), code="ASSET_TYPE_INVALID", status_code=422)
    if isinstance(exc, UnsafeFileNameError):
        return AssetServiceError(str(exc), code="ASSET_NAME_INVALID", status_code=422)
    return AssetServiceError(str(exc), code="ASSET_REFERENCE_INVALID", status_code=422)


def _decode_base64(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except ValueError as exc:
        raise AssetServiceError(
            "asset content_base64 is not valid base64",
            code="ASSET_CONTENT_INVALID",
            status_code=422,
        ) from exc


def _asset_file_path(settings: RuntimeSettings, asset: Asset) -> Path:
    path = (settings.data_root / Path(asset.storage_path)).resolve()
    original_root = (settings.files_dir / "original").resolve()
    if original_root not in path.parents:
        raise AssetServiceError(
            "asset path escaped original file directory",
            code="ASSET_PATH_INVALID",
            status_code=422,
            details={"asset_id": asset.id},
        )
    return path
