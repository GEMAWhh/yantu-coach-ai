from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.models.evidence import AIJob
from app.request_context import get_request_id
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.wrongbook import (
    AttemptCreate,
    AttemptResponse,
    AttemptResultCreate,
    AttemptSubmitResponse,
    AttemptType,
    QuestionAssetLink,
    QuestionAssetResponse,
    QuestionCreate,
    QuestionResponse,
    WrongbookAIJobResponse,
    WrongbookAnalyzeRequest,
    WrongbookAnalyzeResponse,
    WrongbookCandidateListResponse,
    WrongbookCandidateResponse,
    WrongbookConfirmResponse,
    WrongbookDraftCreate,
    WrongbookDraftHistoryItemResponse,
    WrongbookDraftHistoryResponse,
    WrongbookDraftResponse,
    WrongbookDraftUpdate,
    WrongbookHistoryResponse,
    WrongRecordCreate,
    WrongRecordDetailResponse,
    WrongRecordResponse,
    WrongVerificationResponse,
)
from app.settings import get_settings
from app.wrongbook.service import (
    WrongbookError,
    analyze_wrong_record,
    confirm_wrongbook_draft,
    create_question,
    create_wrong_record,
    create_wrongbook_draft,
    get_wrong_record,
    get_wrong_verification,
    get_wrongbook_draft,
    link_question_asset,
    list_wrong_attempts,
    list_wrongbook_draft_history,
    list_wrongbook_planning_candidates,
    submit_attempt,
    update_wrongbook_draft,
)

router = APIRouter(prefix="/api/v1/wrongbook", tags=["wrongbook"])
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.post("/questions", response_model=ApiResponse[QuestionResponse])
def create_question_endpoint(
    request: Request,
    payload: QuestionCreate,
) -> ApiResponse[QuestionResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            question = create_question(session, **payload.model_dump())
            response = QuestionResponse.from_model(question)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post("/records", response_model=ApiResponse[WrongRecordDetailResponse])
def create_wrong_record_endpoint(
    request: Request,
    payload: WrongRecordCreate,
) -> ApiResponse[WrongRecordDetailResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            record = create_wrong_record(session, **payload.model_dump())
            verification = get_wrong_verification(session, record.id)
            response = WrongRecordDetailResponse(
                record=WrongRecordResponse.from_model(record),
                verification=WrongVerificationResponse.from_model(verification),
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.get("/planning-candidates", response_model=ApiResponse[WrongbookCandidateListResponse])
def planning_candidates(request: Request) -> ApiResponse[WrongbookCandidateListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [
            WrongbookCandidateResponse.from_candidate(candidate)
            for candidate in list_wrongbook_planning_candidates(session)
        ]
    return api_response(WrongbookCandidateListResponse(items=items, total=len(items)), request)


@router.post("/drafts", response_model=ApiResponse[WrongbookAnalyzeResponse])
def create_wrongbook_manual_draft(
    request: Request,
    payload: WrongbookDraftCreate,
) -> ApiResponse[WrongbookAnalyzeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = create_wrongbook_draft(
                session,
                payload.wrong_record_id,
                structured_json=payload.structured_json,
            )
            ai_job = session.get(AIJob, draft.ai_job_id)
            if ai_job is None:
                raise WrongbookError(
                    "wrongbook ai job not found",
                    code="WRONGBOOK_AI_JOB_NOT_FOUND",
                    status_code=404,
                    details={"ai_job_id": draft.ai_job_id},
                )
            response = WrongbookAnalyzeResponse(
                draft=WrongbookDraftResponse.from_model(draft),
                ai_job=WrongbookAIJobResponse.from_model(ai_job),
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.get("/history", response_model=ApiResponse[WrongbookDraftHistoryResponse])
def wrongbook_draft_history(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[WrongbookDraftHistoryResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [
            WrongbookDraftHistoryItemResponse.from_item(item)
            for item in list_wrongbook_draft_history(session, limit=limit)
        ]
    return api_response(WrongbookDraftHistoryResponse(items=items, total=len(items)), request)


@router.get("/{wrong_record_id}", response_model=ApiResponse[WrongRecordDetailResponse])
def get_wrong_record_endpoint(
    request: Request,
    wrong_record_id: str,
) -> ApiResponse[WrongRecordDetailResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            record = get_wrong_record(session, wrong_record_id)
            verification = get_wrong_verification(session, wrong_record_id)
            response = WrongRecordDetailResponse(
                record=WrongRecordResponse.from_model(record),
                verification=WrongVerificationResponse.from_model(verification),
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post("/{wrong_record_id}/analyze", response_model=ApiResponse[WrongbookAnalyzeResponse])
def analyze_wrongbook_record(
    request: Request,
    wrong_record_id: str,
    payload: WrongbookAnalyzeRequest,
) -> ApiResponse[WrongbookAnalyzeResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = analyze_wrong_record(
                session,
                wrong_record_id,
                provider_mode=payload.provider_mode,
            )
            ai_job = session.get(AIJob, draft.ai_job_id)
            if ai_job is None:
                raise WrongbookError(
                    "wrongbook ai job not found",
                    code="WRONGBOOK_AI_JOB_NOT_FOUND",
                    status_code=404,
                    details={"ai_job_id": draft.ai_job_id},
                )
            response = WrongbookAnalyzeResponse(
                draft=WrongbookDraftResponse.from_model(draft),
                ai_job=WrongbookAIJobResponse.from_model(ai_job),
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.get("/{wrong_record_id}/draft", response_model=ApiResponse[WrongbookDraftResponse])
def get_wrongbook_record_draft(
    request: Request,
    wrong_record_id: str,
) -> ApiResponse[WrongbookDraftResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = WrongbookDraftResponse.from_model(
                get_wrongbook_draft(session, wrong_record_id)
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.patch("/{wrong_record_id}/draft", response_model=ApiResponse[WrongbookDraftResponse])
def update_wrongbook_record_draft(
    request: Request,
    wrong_record_id: str,
    payload: WrongbookDraftUpdate,
) -> ApiResponse[WrongbookDraftResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            draft = update_wrongbook_draft(
                session,
                wrong_record_id,
                structured_json=payload.structured_json,
            )
            response = WrongbookDraftResponse.from_model(draft)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post("/{wrong_record_id}/confirm", response_model=ApiResponse[WrongbookConfirmResponse])
def confirm_wrongbook_record_draft(
    request: Request,
    wrong_record_id: str,
) -> ApiResponse[WrongbookConfirmResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            confirmation = confirm_wrongbook_draft(
                session,
                wrong_record_id,
                request_id=get_request_id(request),
            )
            response = WrongbookConfirmResponse.from_confirmation(confirmation)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.get("/{wrong_record_id}/history", response_model=ApiResponse[WrongbookHistoryResponse])
def get_wrong_history_endpoint(
    request: Request,
    wrong_record_id: str,
) -> ApiResponse[WrongbookHistoryResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            record = get_wrong_record(session, wrong_record_id)
            verification = get_wrong_verification(session, wrong_record_id)
            attempts = list_wrong_attempts(session, wrong_record_id)
            response = WrongbookHistoryResponse(
                record=WrongRecordResponse.from_model(record),
                verification=WrongVerificationResponse.from_model(verification),
                attempts=[AttemptResponse.from_model(attempt) for attempt in attempts],
                total_attempts=len(attempts),
            )
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post("/{wrong_record_id}/assets", response_model=ApiResponse[QuestionAssetResponse])
def link_asset(
    request: Request,
    wrong_record_id: str,
    payload: QuestionAssetLink,
) -> ApiResponse[QuestionAssetResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            asset = link_question_asset(
                session,
                wrong_record_id=wrong_record_id,
                **payload.model_dump(),
            )
            response = QuestionAssetResponse.from_model(asset)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post("/{wrong_record_id}/attempts", response_model=ApiResponse[AttemptSubmitResponse])
def submit_wrong_attempt(
    request: Request,
    wrong_record_id: str,
    payload: AttemptCreate,
    idempotency_key: IdempotencyKey = None,
) -> ApiResponse[AttemptSubmitResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            submission = submit_attempt(
                session,
                wrong_record_id,
                idempotency_key=idempotency_key,
                request_id=get_request_id(request),
                **payload.model_dump(),
            )
            response = AttemptSubmitResponse.from_submission(submission)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


@router.post(
    "/{wrong_record_id}/variant-results", response_model=ApiResponse[AttemptSubmitResponse]
)
def submit_wrong_variant_result(
    request: Request,
    wrong_record_id: str,
    payload: AttemptResultCreate,
    idempotency_key: IdempotencyKey = None,
) -> ApiResponse[AttemptSubmitResponse]:
    return _submit_fixed_attempt(
        request,
        wrong_record_id,
        attempt_type="variant",
        payload=payload,
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{wrong_record_id}/interval-results", response_model=ApiResponse[AttemptSubmitResponse]
)
def submit_wrong_interval_result(
    request: Request,
    wrong_record_id: str,
    payload: AttemptResultCreate,
    idempotency_key: IdempotencyKey = None,
) -> ApiResponse[AttemptSubmitResponse]:
    return _submit_fixed_attempt(
        request,
        wrong_record_id,
        attempt_type="interval_test",
        payload=payload,
        idempotency_key=idempotency_key,
    )


def _submit_fixed_attempt(
    request: Request,
    wrong_record_id: str,
    *,
    attempt_type: AttemptType,
    payload: AttemptResultCreate,
    idempotency_key: str | None,
) -> ApiResponse[AttemptSubmitResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            submission = submit_attempt(
                session,
                wrong_record_id,
                attempt_type=attempt_type,
                idempotency_key=idempotency_key,
                request_id=get_request_id(request),
                **payload.model_dump(),
            )
            response = AttemptSubmitResponse.from_submission(submission)
    except WrongbookError as exc:
        raise _api_wrongbook_error(exc) from exc
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_wrongbook_error(exc: WrongbookError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
