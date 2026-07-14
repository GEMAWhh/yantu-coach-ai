from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.files.backup import BackupManifest


class BackupCreateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(default="manual", min_length=1, max_length=40)


class BackupEntryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    size: int
    sha256: str


class BackupManifestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    created_at: str
    database: BackupEntryResponse
    files: list[BackupEntryResponse]
    manifest_hash: str

    @classmethod
    def from_manifest(cls, manifest: BackupManifest) -> "BackupManifestResponse":
        return cls(
            version=manifest["version"],
            created_at=manifest["created_at"],
            database=BackupEntryResponse(**manifest["database"]),
            files=[BackupEntryResponse(**entry) for entry in manifest["files"]],
            manifest_hash=manifest["manifest_hash"],
        )


class BackupResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    backup_id: str
    size_bytes: int
    created_at: datetime
    manifest: BackupManifestResponse | None = None
    pre_restore_backup_id: str | None = None


class BackupListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[BackupResponse]
    total: int
