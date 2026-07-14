import json
import shutil
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, TypedDict, cast
from uuid import uuid4

from app.db.database import get_engine
from app.db.migrations import initialize_database
from app.files.exceptions import BackupIntegrityError
from app.settings import RuntimeSettings


class BackupEntry(TypedDict):
    path: str
    size: int
    sha256: str


class BackupManifest(TypedDict):
    version: str
    created_at: str
    database: BackupEntry
    files: list[BackupEntry]
    manifest_hash: str


@dataclass(frozen=True)
class BackupResult:
    path: Path
    manifest: BackupManifest
    pre_restore_backup: Path | None = None


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(path: Path, relative_path: str) -> BackupEntry:
    return {"path": relative_path, "size": path.stat().st_size, "sha256": _hash_file(path)}


def _manifest_hash(manifest_without_hash: dict[str, Any]) -> str:
    payload = json.dumps(
        manifest_without_hash,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _hash_bytes(payload)


def _backup_sqlite_database(settings: RuntimeSettings, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(settings.database_path)
    target = sqlite3.connect(destination)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _copy_files_tree(settings: RuntimeSettings, destination_root: Path) -> list[BackupEntry]:
    entries: list[BackupEntry] = []
    for source_root in [settings.files_dir, settings.settings_dir]:
        if not source_root.exists():
            continue
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative_path = source.relative_to(settings.data_root).as_posix()
            target = destination_root / Path(relative_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            entries.append(_entry(target, relative_path))
    return entries


def create_backup(settings: RuntimeSettings, *, label: str = "manual") -> BackupResult:
    initialize_database(settings)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{label}-{timestamp}-{uuid4().hex}.zip"
    backup_path = settings.backups_dir / backup_name
    settings.backups_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=settings.cache_dir) as tmp:
        staging = Path(tmp)
        database_copy = staging / "database" / "study.db"
        _backup_sqlite_database(settings, database_copy)
        files = _copy_files_tree(settings, staging)
        manifest_core: dict[str, Any] = {
            "version": "backup-v1",
            "created_at": datetime.now(UTC).isoformat(),
            "database": _entry(database_copy, "database/study.db"),
            "files": files,
        }
        manifest: BackupManifest = cast(
            BackupManifest,
            {**manifest_core, "manifest_hash": _manifest_hash(manifest_core)},
        )
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(item for item in staging.rglob("*") if item.is_file()):
                archive.write(path, path.relative_to(staging).as_posix())

    return BackupResult(path=backup_path, manifest=verify_backup(backup_path))


def _assert_safe_zip_name(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise BackupIntegrityError("backup contains unsafe path")


def _load_manifest(archive: zipfile.ZipFile) -> BackupManifest:
    if "manifest.json" not in archive.namelist():
        raise BackupIntegrityError("backup manifest is missing")
    raw = json.loads(archive.read("manifest.json").decode("utf-8"))
    if not isinstance(raw, dict):
        raise BackupIntegrityError("backup manifest is invalid")
    manifest = cast(BackupManifest, raw)
    manifest_hash = manifest.get("manifest_hash")
    manifest_core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if manifest_hash != _manifest_hash(manifest_core):
        raise BackupIntegrityError("backup manifest hash mismatch")
    return manifest


def verify_backup(backup_path: Path) -> BackupManifest:
    try:
        with zipfile.ZipFile(backup_path, "r") as archive:
            for name in archive.namelist():
                _assert_safe_zip_name(name)
            manifest = _load_manifest(archive)
            entries = [manifest["database"], *manifest["files"]]
            names = set(archive.namelist())
            for entry in entries:
                if entry["path"] not in names:
                    raise BackupIntegrityError(f"backup entry missing: {entry['path']}")
                data = archive.read(entry["path"])
                if len(data) != entry["size"] or _hash_bytes(data) != entry["sha256"]:
                    raise BackupIntegrityError(f"backup entry hash mismatch: {entry['path']}")
            return manifest
    except zipfile.BadZipFile as exc:
        raise BackupIntegrityError("backup is not a valid zip file") from exc


def restore_backup(settings: RuntimeSettings, backup_path: Path) -> BackupResult:
    manifest = verify_backup(backup_path)
    pre_restore = create_backup(settings, label="pre-restore").path

    with tempfile.TemporaryDirectory(dir=settings.cache_dir) as tmp:
        staging = Path(tmp)
        with zipfile.ZipFile(backup_path, "r") as archive:
            archive.extractall(staging)

        engine = get_engine(settings.database_url)
        engine.dispose()

        settings.database_dir.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            existing = Path(f"{settings.database_path}{suffix}")
            if existing.exists():
                existing.unlink()
        shutil.copy2(staging / "database" / "study.db", settings.database_path)

        if settings.files_dir.exists():
            shutil.rmtree(settings.files_dir)
        backup_files = staging / "files"
        if backup_files.exists():
            shutil.copytree(backup_files, settings.files_dir)
        if settings.settings_dir.exists():
            shutil.rmtree(settings.settings_dir)
        backup_settings = staging / "settings"
        if backup_settings.exists():
            shutil.copytree(backup_settings, settings.settings_dir)
        settings.ensure_runtime_dirs()

    return BackupResult(path=backup_path, manifest=manifest, pre_restore_backup=pre_restore)
