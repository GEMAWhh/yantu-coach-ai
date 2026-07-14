from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.imports.localstorage import LocalStorageCommitResult, LocalStoragePreview


class LocalStorageImportPreviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_key: Literal["postgradCoachV11"]
    source_sha256: str = Field(min_length=64, max_length=64)
    source_version: str
    size_bytes: int
    recognized_fields: list[str]
    unknown_fields: list[str]
    entity_counts: dict[str, int]
    mastery_status: Literal["none", "imported_unverified"]
    report: dict[str, Any]

    @classmethod
    def from_preview(cls, preview: LocalStoragePreview) -> "LocalStorageImportPreviewResponse":
        return cls(
            source_key="postgradCoachV11",
            source_sha256=preview.source_sha256,
            source_version=preview.source_version,
            size_bytes=preview.size_bytes,
            recognized_fields=preview.recognized_fields,
            unknown_fields=preview.unknown_fields,
            entity_counts=preview.entity_counts,
            mastery_status=preview.mastery_status,
            report=preview.report,
        )


class LocalStorageImportCommitResponse(LocalStorageImportPreviewResponse):
    batch_id: str
    created: bool
    status: Literal["committed"]

    @classmethod
    def from_commit_result(
        cls, result: LocalStorageCommitResult
    ) -> "LocalStorageImportCommitResponse":
        preview = result.preview
        return cls(
            batch_id=result.batch_id,
            created=result.created,
            status="committed",
            source_key="postgradCoachV11",
            source_sha256=preview.source_sha256,
            source_version=preview.source_version,
            size_bytes=preview.size_bytes,
            recognized_fields=preview.recognized_fields,
            unknown_fields=preview.unknown_fields,
            entity_counts=preview.entity_counts,
            mastery_status=preview.mastery_status,
            report=preview.report,
        )
