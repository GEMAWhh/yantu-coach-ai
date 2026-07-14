from typing import Annotated

from fastapi import APIRouter, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.request_context import get_request_id
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.wrongbook import (
    AttemptCreate,
    AttemptSubmitResponse,
    QuestionAssetLink,
    QuestionAssetResponse,
    QuestionCreate,
    QuestionResponse,
    WrongbookCandidateListResponse,
    WrongbookCandidateResponse,
    WrongRecordCreate,
    WrongRecordDetailResponse,
    WrongRecordResponse,
    WrongVerificationResponse,
)
from app.settings import get_settings
from app.wrongbook.service import (
    WrongbookError,
    create_question,
    create_wrong_record,
    get_wrong_record,
    get_wrong_verification,
    link_question_asset,
    list_wrongbook_planning_candidates,
    submit_attempt,
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
