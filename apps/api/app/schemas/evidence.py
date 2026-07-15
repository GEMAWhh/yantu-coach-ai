from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.evidence.service import EvidenceHistoryItem
from app.models.asset import Asset
from app.models.evidence import AIJob, EvidenceDraft, EvidenceRecord

EvidenceRecordStatus = Literal["pending", "confirmed", "rejected"]
EvidenceDraftStatus = Literal["draft", "needs_correction", "confirmed", "rejected"]
AIJobStatus = Literal["queued", "running", "succeeded", "failed"]
ProviderMode = Literal["valid", "invalid_schema"]


class EvidenceFileUpload(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_name: str = Field(min_length=1, max_length=255)
    mime_type: Literal["image/png", "image/jpeg", "application/pdf"]
    content_base64: str = Field(min_length=1)


class EvidenceUploadRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    study_date: date
    subject_id: str | None = None
    files: list[EvidenceFileUpload] = Field(min_length=1)


class EvidenceAssetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    original_name: str
    storage_path: str
    mime_type: str
    size_bytes: int
    state: str
    reference_count: int
    page_order: int

    @classmethod
    def from_model(cls, asset: Asset, *, page_order: int) -> EvidenceAssetResponse:
        return cls(
            id=asset.id,
            version=asset.version,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
            original_name=asset.original_name,
            storage_path=asset.storage_path,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            state=asset.state,
            reference_count=asset.reference_count,
            page_order=page_order,
        )


class EvidenceRecordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    study_date: date
    subject_id: str | None
    status: EvidenceRecordStatus
    asset_count: int
    confirmed_facts: dict[str, Any] | None
    inferences: dict[str, Any] | None
    uncertain_fields: list[dict[str, Any]] | None
    teaching_judgment: dict[str, Any] | None
    suggested_actions: list[dict[str, Any]] | None
    confirmed_at: datetime | None
    rejected_at: datetime | None

    @classmethod
    def from_model(cls, record: EvidenceRecord) -> EvidenceRecordResponse:
        return cls(
            id=record.id,
            version=record.version,
            created_at=record.created_at,
            updated_at=record.updated_at,
            created_by=record.created_by,
            study_date=record.study_date,
            subject_id=record.subject_id,
            status=cast(EvidenceRecordStatus, record.status),
            asset_count=record.asset_count,
            confirmed_facts=record.confirmed_facts_json,
            inferences=record.inferences_json,
            uncertain_fields=record.uncertain_fields_json,
            teaching_judgment=record.teaching_judgment_json,
            suggested_actions=record.suggested_actions_json,
            confirmed_at=record.confirmed_at,
            rejected_at=record.rejected_at,
        )


class EvidenceUploadResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: EvidenceRecordResponse
    assets: list[EvidenceAssetResponse]


class EvidenceHistoryItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: EvidenceRecordResponse
    draft: EvidenceDraftResponse | None

    @classmethod
    def from_item(cls, item: EvidenceHistoryItem) -> EvidenceHistoryItemResponse:
        return cls(
            record=EvidenceRecordResponse.from_model(item.record),
            draft=(
                EvidenceDraftResponse.from_model(item.draft) if item.draft is not None else None
            ),
        )


class EvidenceHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[EvidenceHistoryItemResponse]
    total: int


class AIJobResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    job_type: str
    provider: str
    model_name: str
    prompt_version: str
    status: AIJobStatus
    attempts: int
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, job: AIJob) -> AIJobResponse:
        return cls(
            id=job.id,
            version=job.version,
            created_at=job.created_at,
            updated_at=job.updated_at,
            job_type=job.job_type,
            provider=job.provider,
            model_name=job.model_name,
            prompt_version=job.prompt_version,
            status=cast(AIJobStatus, job.status),
            attempts=job.attempts,
            input_json=job.input_json,
            output_json=job.output_json,
            error_code=job.error_code,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )


class EvidenceDraftResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    evidence_record_id: str
    ai_job_id: str
    status: EvidenceDraftStatus
    schema_version: Literal["evidence-analysis-v1"]
    structured_json: dict[str, Any]
    validation_errors: list[str]
    confirmed_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    confirmed_once: bool

    @classmethod
    def from_model(cls, draft: EvidenceDraft) -> EvidenceDraftResponse:
        return cls(
            id=draft.id,
            version=draft.version,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            evidence_record_id=draft.evidence_record_id,
            ai_job_id=draft.ai_job_id,
            status=cast(EvidenceDraftStatus, draft.status),
            schema_version="evidence-analysis-v1",
            structured_json=draft.structured_json,
            validation_errors=draft.validation_errors_json,
            confirmed_at=draft.confirmed_at,
            rejected_at=draft.rejected_at,
            rejection_reason=draft.rejection_reason,
            confirmed_once=draft.confirmed_once,
        )


class EvidenceAnalyzeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_mode: ProviderMode = "valid"


class EvidenceAnalyzeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    draft: EvidenceDraftResponse
    ai_job: AIJobResponse


class EvidenceDraftUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    structured_json: dict[str, Any]


class EvidenceConfirmResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: EvidenceRecordResponse
    draft: EvidenceDraftResponse
    created: bool


class EvidenceRejectRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    reason: str = Field(min_length=1, max_length=500)
