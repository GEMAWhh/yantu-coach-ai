import zipfile
from collections.abc import Generator
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.assets.service import read_asset_content
from app.db.database import get_session_factory
from app.db.migrations import initialize_database
from app.files.backup import create_backup, restore_backup, verify_backup
from app.files.exceptions import BackupIntegrityError, FileReferenceError, UnsupportedFileTypeError
from app.files.storage import (
    delete_asset_file_if_unreferenced,
    release_asset_reference,
    store_original_file,
)
from app.models.asset import Asset
from app.settings import RuntimeSettings, SupabaseStorageSettings, get_settings

PNG_BYTES = b"\x89PNG\r\n\x1a\nlocal-test-png"
JPEG_BYTES = b"\xff\xd8\xff\xe0local-test-jpeg"
PDF_BYTES = b"%PDF-1.7\nlocal-test-pdf"


@pytest.fixture
def test_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Generator[RuntimeSettings, None, None]:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    get_settings.cache_clear()
    settings = get_settings()
    initialize_database(settings)
    yield settings
    get_settings.cache_clear()


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_duplicate_files_are_deduplicated_and_reference_safe(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    source = _write(tmp_path / "proof.png", PNG_BYTES)
    session_factory = get_session_factory(test_settings.database_url)

    with session_factory.begin() as session:
        first = store_original_file(
            test_settings,
            session,
            source_path=source,
            original_name="proof.png",
            declared_mime_type="image/png",
        )
        second = store_original_file(
            test_settings,
            session,
            source_path=source,
            original_name="proof.png",
            declared_mime_type="image/png",
        )
        asset_id = first.id
        storage_path = first.storage_path
        assert second.id == asset_id
        assert second.reference_count == 2

    physical_path = test_settings.data_root / storage_path
    assert physical_path.is_file()

    with session_factory.begin() as session:
        release_asset_reference(session, asset_id)
        with pytest.raises(FileReferenceError):
            delete_asset_file_if_unreferenced(test_settings, session, asset_id)
        release_asset_reference(session, asset_id)
        delete_asset_file_if_unreferenced(test_settings, session, asset_id)

    assert not physical_path.exists()


def test_file_storage_rejects_path_traversal_and_masquerade(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    source = _write(tmp_path / "fake.png", PDF_BYTES)
    session_factory = get_session_factory(test_settings.database_url)

    with session_factory.begin() as session:
        with pytest.raises(FileReferenceError):
            release_asset_reference(session, "missing")
        with pytest.raises(ValueError, match="path"):
            store_original_file(
                test_settings,
                session,
                source_path=source,
                original_name="../fake.png",
                declared_mime_type="image/png",
            )
        with pytest.raises(UnsupportedFileTypeError):
            store_original_file(
                test_settings,
                session,
                source_path=source,
                original_name="fake.png",
                declared_mime_type="image/png",
            )


def test_backup_contains_database_files_and_manifest(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    source = _write(tmp_path / "proof.pdf", PDF_BYTES)
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        store_original_file(
            test_settings,
            session,
            source_path=source,
            original_name="proof.pdf",
            declared_mime_type="application/pdf",
        )

    backup = create_backup(test_settings)

    assert backup.path.is_file()
    assert backup.manifest["database"]["path"] == "database/study.db"
    assert backup.manifest["files"][0]["path"].startswith("files/original/")
    assert verify_backup(backup.path) == backup.manifest


def test_restore_creates_pre_restore_backup_and_restores_hashes(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    session_factory = get_session_factory(test_settings.database_url)
    original_source = _write(tmp_path / "original.png", PNG_BYTES)
    extra_source = _write(tmp_path / "extra.jpg", JPEG_BYTES)

    with session_factory.begin() as session:
        original = store_original_file(
            test_settings,
            session,
            source_path=original_source,
            original_name="original.png",
            declared_mime_type="image/png",
        )
        original_storage = original.storage_path
    backup = create_backup(test_settings)

    with session_factory.begin() as session:
        extra = store_original_file(
            test_settings,
            session,
            source_path=extra_source,
            original_name="extra.jpg",
            declared_mime_type="image/jpeg",
        )
        extra_storage = extra.storage_path

    restored = restore_backup(test_settings, backup.path)

    assert restored.pre_restore_backup is not None
    assert restored.pre_restore_backup.is_file()
    assert (test_settings.data_root / original_storage).is_file()
    assert not (test_settings.data_root / extra_storage).exists()
    with session_factory() as session:
        count = session.scalar(select(func.count(Asset.id)))
        assert count == 1


def test_corrupt_or_missing_backup_is_rejected_without_restore(
    test_settings: RuntimeSettings,
    tmp_path: Path,
) -> None:
    source = _write(tmp_path / "proof.png", PNG_BYTES)
    session_factory = get_session_factory(test_settings.database_url)
    with session_factory.begin() as session:
        store_original_file(
            test_settings,
            session,
            source_path=source,
            original_name="proof.png",
            declared_mime_type="image/png",
        )
    backup = create_backup(test_settings)
    before_database = test_settings.database_path.read_bytes()

    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip")
    with pytest.raises(BackupIntegrityError):
        verify_backup(bad_zip)

    missing_entry = tmp_path / "missing-entry.zip"
    with zipfile.ZipFile(backup.path, "r") as source_zip:
        with zipfile.ZipFile(missing_entry, "w") as target_zip:
            for name in source_zip.namelist():
                if name != "database/study.db":
                    target_zip.writestr(name, source_zip.read(name))

    with pytest.raises(BackupIntegrityError):
        restore_backup(test_settings, missing_entry)

    assert test_settings.database_path.read_bytes() == before_database


def test_cloud_storage_preserves_deduplication_read_and_reference_safe_delete(
    test_settings: RuntimeSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cloud_settings = replace(
        test_settings,
        supabase_storage=SupabaseStorageSettings(
            "https://example.supabase.co",
            "fake-secret-key-with-at-least-32-characters",
            "yantu-assets",
        ),
    )
    objects: dict[str, bytes] = {}
    uploads: list[str] = []

    def upload(_self: object, object_path: str, content: bytes, _mime_type: str) -> None:
        uploads.append(object_path)
        objects[object_path] = content

    def download(_self: object, object_path: str) -> bytes:
        return objects[object_path]

    def delete(_self: object, object_path: str) -> None:
        objects.pop(object_path)

    monkeypatch.setattr("app.files.storage.SupabaseObjectStorage.upload", upload)
    monkeypatch.setattr("app.files.storage.SupabaseObjectStorage.delete", delete)
    monkeypatch.setattr("app.assets.service.SupabaseObjectStorage.download", download)
    source = _write(tmp_path / "cloud.png", PNG_BYTES)
    session_factory = get_session_factory(test_settings.database_url)

    with session_factory.begin() as session:
        first = store_original_file(
            cloud_settings,
            session,
            source_path=source,
            original_name="cloud.png",
            declared_mime_type="image/png",
        )
        second = store_original_file(
            cloud_settings,
            session,
            source_path=source,
            original_name="cloud.png",
            declared_mime_type="image/png",
        )
        asset_id = first.id
        storage_path = first.storage_path
        assert second.id == asset_id
        assert second.reference_count == 2

    assert uploads == [storage_path]
    assert not (test_settings.data_root / storage_path).exists()
    with session_factory() as session:
        assert read_asset_content(cloud_settings, session, asset_id).content_base64

    with session_factory.begin() as session:
        release_asset_reference(session, asset_id)
        release_asset_reference(session, asset_id)
        delete_asset_file_if_unreferenced(cloud_settings, session, asset_id)

    assert storage_path not in objects
