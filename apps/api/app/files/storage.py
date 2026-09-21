from hashlib import sha256
from pathlib import Path, PurePosixPath
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.files.exceptions import FileReferenceError, UnsafeFileNameError, UnsupportedFileTypeError
from app.files.object_storage import SupabaseObjectStorage
from app.models.asset import Asset
from app.settings import RuntimeSettings

SUPPORTED_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


def calculate_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_original_name(original_name: str) -> str:
    if not original_name or "/" in original_name or "\\" in original_name:
        raise UnsafeFileNameError("original file name must not contain path separators")
    path = PurePosixPath(original_name)
    if path.name != original_name or any(part in {"", ".", ".."} for part in path.parts):
        raise UnsafeFileNameError("original file name must be a file name, not a path")
    return original_name


def _detect_mime_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def _validated_extension_and_mime(
    original_name: str,
    declared_mime_type: str,
    sample: bytes,
) -> tuple[str, str]:
    extension = Path(original_name).suffix.lower()
    expected_mime = SUPPORTED_MIME_BY_EXTENSION.get(extension)
    detected_mime = _detect_mime_type(sample)
    if expected_mime is None:
        raise UnsupportedFileTypeError("unsupported file extension")
    if declared_mime_type != expected_mime or detected_mime != expected_mime:
        raise UnsupportedFileTypeError("file extension, declared MIME and file signature mismatch")
    return extension, expected_mime


def _asset_storage_path(settings: RuntimeSettings, digest: str, extension: str) -> tuple[Path, str]:
    relative_path = PurePosixPath("files") / "original" / digest[:2] / f"{digest}{extension}"
    absolute_path = (settings.data_root / Path(*relative_path.parts)).resolve()
    original_root = (settings.files_dir / "original").resolve()
    if original_root not in absolute_path.parents:
        raise UnsafeFileNameError("resolved storage path escaped the original file directory")
    return absolute_path, relative_path.as_posix()


def store_original_file(
    settings: RuntimeSettings,
    session: Session,
    *,
    source_path: Path,
    original_name: str,
    declared_mime_type: str,
    state: str = "inbox",
) -> Asset:
    safe_name = _safe_original_name(original_name)
    content = source_path.read_bytes()
    sample = content[:16]
    extension, mime_type = _validated_extension_and_mime(safe_name, declared_mime_type, sample)
    digest = calculate_sha256(source_path)
    size_bytes = source_path.stat().st_size

    for pending in session.new:
        if isinstance(pending, Asset) and pending.sha256 == digest:
            pending.reference_count += 1
            return pending

    existing = session.scalar(select(Asset).where(Asset.sha256 == digest))
    if existing is not None:
        existing.reference_count += 1
        return existing

    absolute_path, relative_path = _asset_storage_path(settings, digest, extension)
    if settings.supabase_storage is not None:
        SupabaseObjectStorage(settings.supabase_storage).upload(relative_path, content, mime_type)
    else:
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        if not absolute_path.exists():
            absolute_path.write_bytes(content)

    asset = Asset(
        id=str(uuid4()),
        sha256=digest,
        original_name=safe_name,
        storage_path=relative_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        state=state,
        reference_count=1,
    )
    session.add(asset)
    return asset


def release_asset_reference(session: Session, asset_id: str) -> Asset:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise FileReferenceError("asset not found")
    if asset.reference_count <= 0:
        raise FileReferenceError("asset reference count is already zero")
    asset.reference_count -= 1
    return asset


def delete_asset_file_if_unreferenced(
    settings: RuntimeSettings, session: Session, asset_id: str
) -> None:
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise FileReferenceError("asset not found")
    if asset.reference_count > 0:
        raise FileReferenceError("asset still has active references")
    if settings.supabase_storage is not None:
        SupabaseObjectStorage(settings.supabase_storage).delete(asset.storage_path)
        return
    path = (settings.data_root / Path(asset.storage_path)).resolve()
    original_root = (settings.files_dir / "original").resolve()
    if original_root not in path.parents:
        raise UnsafeFileNameError("asset path escaped original file directory")
    if path.exists():
        path.unlink()
