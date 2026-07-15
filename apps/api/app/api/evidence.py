from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.evidence.service import (
    EvidenceError,
    EvidenceFileInput,
    analyze_evidence_record,
    confirm_evidence_draft,
    get_evidence_draft,
    list_evidence_history,
    reject_evidence_draft,
    update_evidence_draft,
    upload_evidence_files,
)
from app.files.exceptions import FileReferenceError, UnsafeFileNameError, UnsupportedFileTypeError
from app.models.evidence import AIJob
from app.request_context import get_request_id
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.evidence import (
    AIJobResponse,
    EvidenceAnalyzeRequest,
    EvidenceAnalyzeResponse,
    EvidenceAssetResponse,
    EvidenceConfirmResponse,
    EvidenceDraftResponse,
    EvidenceDraftUpdate,
    EvidenceHistoryItemResponse,
    EvidenceHistoryResponse,
    EvidenceRecordResponse,
    EvidenceRejectRequest,
    EvidenceUploadRequest,
    EvidenceUploadResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


@router.post("/uploads", response_model=ApiResponse[EvidenceUploadResponse])
def upload_evidence(
    request: Request,
    payload: EvidenceUploadRequest,
) -> ApiResponse[EvidenceUploadResponse]:
    settings = get_settings()
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            uploaded = upload_evidence_files(
                settings,
                session,
                study_date=payload.study_date,
                subject_id=payload.subject_id,
                files=[
                    EvidenceFileInput(
                        original_name=file.original_name,
                        mime_type=file.mime_type,
                        content_base64=file.content_base64,
                    )
                    for file in payload.files
                ],
            )
            response = EvidenceUploadResponse(
                record=EvidenceRecordResponse.from_model(uploaded.record),
                assets=[
                    EvidenceAssetResponse.from_model(asset, page_order=index)
                    for index, asset in enumerate(uploaded.assets)
                ],
            )
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    except (FileReferenceError, UnsafeFileNameError, UnsupportedFileTypeError) as exc:
        raise _api_file_error(exc) from exc
    return api_response(response, request)


@router.get("/history", response_model=ApiResponse[EvidenceHistoryResponse])
def evidence_history(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[EvidenceHistoryResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [
            EvidenceHistoryItemResponse.from_item(item)
            for item in list_evidence_history(session, limit=limit)
        ]
    return api_response(EvidenceHistoryResponse(items=items, total=len(items)), request)


@router.post("/{record_id}/analyze", response_model=ApiResponse[EvidenceAnalyzeResponse])
def analyze_evidence(
    request: Request,
    record_id: str,
    payload: EvidenceAnalyzeRequest,
) -> ApiResponse[EvidenceAnalyzeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = analyze_evidence_record(session, record_id, provider_mode=payload.provider_mode)
            ai_job = session.get(AIJob, draft.ai_job_id)
            if ai_job is None:
                raise EvidenceError(
                    "evidence ai job not found",
                    code="EVIDENCE_AI_JOB_NOT_FOUND",
                    status_code=404,
                    details={"ai_job_id": draft.ai_job_id},
                )
            response = EvidenceAnalyzeResponse(
                draft=EvidenceDraftResponse.from_model(draft),
                ai_job=AIJobResponse.from_model(ai_job),
            )
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    return api_response(response, request)


@router.get("/{record_id}/draft", response_model=ApiResponse[EvidenceDraftResponse])
def get_draft(request: Request, record_id: str) -> ApiResponse[EvidenceDraftResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = EvidenceDraftResponse.from_model(get_evidence_draft(session, record_id))
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    return api_response(response, request)


@router.patch("/{record_id}/draft", response_model=ApiResponse[EvidenceDraftResponse])
def update_draft(
    request: Request,
    record_id: str,
    payload: EvidenceDraftUpdate,
) -> ApiResponse[EvidenceDraftResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = update_evidence_draft(
                session,
                record_id,
                structured_json=payload.structured_json,
            )
            response = EvidenceDraftResponse.from_model(draft)
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    return api_response(response, request)


@router.post("/{record_id}/confirm", response_model=ApiResponse[EvidenceConfirmResponse])
def confirm_draft(request: Request, record_id: str) -> ApiResponse[EvidenceConfirmResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            confirmation = confirm_evidence_draft(
                session,
                record_id,
                request_id=get_request_id(request),
            )
            response = EvidenceConfirmResponse(
                record=EvidenceRecordResponse.from_model(confirmation.record),
                draft=EvidenceDraftResponse.from_model(confirmation.draft),
                created=confirmation.created,
            )
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    return api_response(response, request)


@router.post("/{record_id}/reject", response_model=ApiResponse[EvidenceDraftResponse])
def reject_draft(
    request: Request,
    record_id: str,
    payload: EvidenceRejectRequest,
) -> ApiResponse[EvidenceDraftResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = reject_evidence_draft(session, record_id, reason=payload.reason)
            response = EvidenceDraftResponse.from_model(draft)
    except EvidenceError as exc:
        raise _api_evidence_error(exc) from exc
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_evidence_error(exc: EvidenceError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )


def _api_file_error(
    exc: FileReferenceError | UnsafeFileNameError | UnsupportedFileTypeError,
) -> ApiError:
    return ApiError(
        status_code=422,
        code="EVIDENCE_FILE_INVALID",
        message=str(exc),
    )
