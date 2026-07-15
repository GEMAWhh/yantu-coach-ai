from __future__ import annotations

from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.models.evidence import AIJob
from app.models.wrongbook import (
    Attempt,
    Question,
    QuestionAsset,
    WrongbookDraft,
    WrongRecord,
    WrongVerification,
)
from app.planning.engine import PlanningCandidate
from app.wrongbook.service import (
    AttemptSubmission,
    WrongbookConfirmation,
    WrongbookDraftHistoryItem,
)

AssetRole = Literal[
    "statement",
    "figure",
    "my_answer",
    "marking",
    "standard_answer",
    "original_solution",
    "supplement",
]
AttemptType = Literal[
    "original_redo",
    "no_hint_redo",
    "variant",
    "interval_test",
    "transfer_test",
]
WrongStatus = Literal[
    "pending_analysis",
    "pending_no_hint_redo",
    "pending_variant",
    "pending_interval",
    "stable_corrected",
    "regressed",
]
WrongbookDraftStatus = Literal["draft", "needs_correction", "confirmed"]
AIJobStatus = Literal["queued", "running", "succeeded", "failed"]
ProviderMode = Literal["valid", "invalid_schema"]


class QuestionCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    standard_text: str = Field(min_length=1)
    subject_id: str | None = None
    knowledge_node_id: str | None = None
    question_type: str | None = Field(default=None, max_length=80)
    difficulty: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=120)
    source_year: int | None = Field(default=None, ge=0)
    source_page: str | None = Field(default=None, max_length=80)
    status: str = Field(default="active", min_length=1, max_length=40)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    is_deleted: bool
    deleted_at: datetime | None
    subject_id: str | None
    knowledge_node_id: str | None
    standard_text: str
    question_type: str | None
    difficulty: str | None
    source: str | None
    source_year: int | None
    source_page: str | None
    status: str

    @classmethod
    def from_model(cls, question: Question) -> QuestionResponse:
        return cls(
            id=question.id,
            version=question.version,
            created_at=question.created_at,
            updated_at=question.updated_at,
            created_by=question.created_by,
            is_deleted=question.is_deleted,
            deleted_at=question.deleted_at,
            subject_id=question.subject_id,
            knowledge_node_id=question.knowledge_node_id,
            standard_text=question.standard_text,
            question_type=question.question_type,
            difficulty=question.difficulty,
            source=question.source,
            source_year=question.source_year,
            source_page=question.source_page,
            status=question.status,
        )


class WrongRecordCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    knowledge_node_id: str | None = None
    surface_cause: str | None = None
    deep_cause: str | None = None
    prerequisite_gap: str | None = None
    error_count: int = Field(default=1, ge=1)
    next_review_at: datetime | None = None


class WrongVerificationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    wrong_record_id: str
    original_redo_passed: bool
    no_hint_redo_passed: bool
    variant_passed: bool
    interval_test_passed: bool
    transfer_test_passed: bool
    last_attempt_id: str | None

    @classmethod
    def from_model(cls, verification: WrongVerification) -> WrongVerificationResponse:
        return cls(
            id=verification.id,
            version=verification.version,
            created_at=verification.created_at,
            updated_at=verification.updated_at,
            wrong_record_id=verification.wrong_record_id,
            original_redo_passed=verification.original_redo_passed,
            no_hint_redo_passed=verification.no_hint_redo_passed,
            variant_passed=verification.variant_passed,
            interval_test_passed=verification.interval_test_passed,
            transfer_test_passed=verification.transfer_test_passed,
            last_attempt_id=verification.last_attempt_id,
        )


class WrongRecordResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    question_id: str
    knowledge_node_id: str | None
    surface_cause: str | None
    deep_cause: str | None
    prerequisite_gap: str | None
    error_count: int
    redo_count: int
    current_status: WrongStatus
    next_review_at: datetime | None
    resolved_at: datetime | None

    @classmethod
    def from_model(cls, wrong: WrongRecord) -> WrongRecordResponse:
        return cls(
            id=wrong.id,
            version=wrong.version,
            created_at=wrong.created_at,
            updated_at=wrong.updated_at,
            created_by=wrong.created_by,
            question_id=wrong.question_id,
            knowledge_node_id=wrong.knowledge_node_id,
            surface_cause=wrong.surface_cause,
            deep_cause=wrong.deep_cause,
            prerequisite_gap=wrong.prerequisite_gap,
            error_count=wrong.error_count,
            redo_count=wrong.redo_count,
            current_status=cast(WrongStatus, wrong.current_status),
            next_review_at=wrong.next_review_at,
            resolved_at=wrong.resolved_at,
        )


class WrongRecordDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: WrongRecordResponse
    verification: WrongVerificationResponse


class QuestionAssetLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset_id: str
    asset_role: AssetRole
    page_order: int = Field(default=0, ge=0)


class QuestionAssetResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    question_id: str
    asset_id: str
    asset_role: AssetRole
    page_order: int

    @classmethod
    def from_model(cls, asset: QuestionAsset) -> QuestionAssetResponse:
        return cls(
            id=asset.id,
            question_id=asset.question_id,
            asset_id=asset.asset_id,
            asset_role=cast(AssetRole, asset.asset_role),
            page_order=asset.page_order,
        )


class AttemptCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt_type: AttemptType
    is_correct: bool
    attempted_at: datetime | None = None
    answer_text: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    duration_seconds: int | None = Field(default=None, ge=0)
    hint_level: int | None = Field(default=None, ge=0)
    confidence: int | None = Field(default=None, ge=0, le=100)


class AttemptResultCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_correct: bool
    attempted_at: datetime | None = None
    answer_text: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    duration_seconds: int | None = Field(default=None, ge=0)
    hint_level: int | None = Field(default=None, ge=0)
    confidence: int | None = Field(default=None, ge=0, le=100)


class AttemptResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    question_id: str
    wrong_record_id: str
    idempotency_key: str | None
    attempt_type: AttemptType
    attempted_at: datetime
    answer_text: str | None
    is_correct: bool
    score: int | None
    duration_seconds: int | None
    hint_level: int | None
    confidence: int | None
    request_id: str | None

    @classmethod
    def from_model(cls, attempt: Attempt) -> AttemptResponse:
        return cls(
            id=attempt.id,
            version=attempt.version,
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
            created_by=attempt.created_by,
            question_id=attempt.question_id,
            wrong_record_id=attempt.wrong_record_id,
            idempotency_key=attempt.idempotency_key,
            attempt_type=cast(AttemptType, attempt.attempt_type),
            attempted_at=attempt.attempted_at,
            answer_text=attempt.answer_text,
            is_correct=attempt.is_correct,
            score=attempt.score,
            duration_seconds=attempt.duration_seconds,
            hint_level=attempt.hint_level,
            confidence=attempt.confidence,
            request_id=attempt.request_id,
        )


class AttemptSubmitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    attempt: AttemptResponse
    record: WrongRecordResponse
    verification: WrongVerificationResponse
    created: bool

    @classmethod
    def from_submission(cls, submission: AttemptSubmission) -> AttemptSubmitResponse:
        return cls(
            attempt=AttemptResponse.from_model(submission.attempt),
            record=WrongRecordResponse.from_model(submission.wrong_record),
            verification=WrongVerificationResponse.from_model(submission.verification),
            created=submission.created,
        )


class WrongbookHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: WrongRecordResponse
    verification: WrongVerificationResponse
    attempts: list[AttemptResponse]
    total_attempts: int


class WrongbookAIJobResponse(BaseModel):
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
    input_json: dict[str, object]
    output_json: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, job: AIJob) -> WrongbookAIJobResponse:
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


class WrongbookDraftResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    wrong_record_id: str
    ai_job_id: str
    status: WrongbookDraftStatus
    schema_version: Literal["wrongbook-analysis-v1"]
    structured_json: dict[str, object]
    validation_errors: list[str]
    confirmed_at: datetime | None
    confirmed_once: bool

    @classmethod
    def from_model(cls, draft: WrongbookDraft) -> WrongbookDraftResponse:
        return cls(
            id=draft.id,
            version=draft.version,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            wrong_record_id=draft.wrong_record_id,
            ai_job_id=draft.ai_job_id,
            status=cast(WrongbookDraftStatus, draft.status),
            schema_version="wrongbook-analysis-v1",
            structured_json=draft.structured_json,
            validation_errors=draft.validation_errors_json,
            confirmed_at=draft.confirmed_at,
            confirmed_once=draft.confirmed_once,
        )


class WrongbookDraftHistoryItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: WrongRecordResponse
    verification: WrongVerificationResponse
    draft: WrongbookDraftResponse | None

    @classmethod
    def from_item(cls, item: WrongbookDraftHistoryItem) -> WrongbookDraftHistoryItemResponse:
        return cls(
            record=WrongRecordResponse.from_model(item.wrong_record),
            verification=WrongVerificationResponse.from_model(item.verification),
            draft=WrongbookDraftResponse.from_model(item.draft) if item.draft is not None else None,
        )


class WrongbookDraftHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WrongbookDraftHistoryItemResponse]
    total: int


class WrongbookAnalyzeRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider_mode: ProviderMode = "valid"


class WrongbookDraftCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    wrong_record_id: str
    structured_json: dict[str, object]


class WrongbookAnalyzeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    draft: WrongbookDraftResponse
    ai_job: WrongbookAIJobResponse


class WrongbookDraftUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    structured_json: dict[str, object]


class WrongbookConfirmResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: WrongRecordResponse
    draft: WrongbookDraftResponse
    created: bool

    @classmethod
    def from_confirmation(cls, confirmation: WrongbookConfirmation) -> WrongbookConfirmResponse:
        return cls(
            record=WrongRecordResponse.from_model(confirmation.wrong_record),
            draft=WrongbookDraftResponse.from_model(confirmation.draft),
            created=confirmation.created,
        )


class WrongbookCandidateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    subject_id: str
    estimated_minutes: int
    cognitive_load: Literal["low", "medium", "high"]
    source_type: str
    source_id: str | None
    task_type: str
    difficulty: str | None
    review_due: int
    knowledge_importance: int
    weakness: int
    repeat_error: int

    @classmethod
    def from_candidate(cls, candidate: PlanningCandidate) -> WrongbookCandidateResponse:
        return cls(
            id=candidate.id,
            title=candidate.title,
            subject_id=candidate.subject_id,
            estimated_minutes=candidate.estimated_minutes,
            cognitive_load=candidate.cognitive_load,
            source_type=candidate.source_type,
            source_id=candidate.source_id,
            task_type=candidate.task_type,
            difficulty=candidate.difficulty,
            review_due=candidate.review_due,
            knowledge_importance=candidate.knowledge_importance,
            weakness=candidate.weakness,
            repeat_error=candidate.repeat_error,
        )


class WrongbookCandidateListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WrongbookCandidateResponse]
    total: int
