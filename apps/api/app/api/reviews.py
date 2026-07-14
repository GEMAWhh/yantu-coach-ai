from datetime import date
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.knowledge.service import KnowledgeError
from app.mastery.service import MasteryServiceError
from app.request_context import get_request_id
from app.responses import api_response
from app.reviews.service import (
    ReviewError,
    list_due_reviews,
    recalculate_review_schedules,
    submit_review_result,
)
from app.schemas.common import ApiResponse
from app.schemas.reviews import (
    DueReviewListResponse,
    DueReviewResponse,
    ReviewRecalculateResponse,
    ReviewResultCreate,
    ReviewResultSubmitResponse,
    ReviewScheduleResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.get("/due", response_model=ApiResponse[DueReviewListResponse])
def due_reviews(
    request: Request,
    date_value: Annotated[date, Query(alias="date")],
) -> ApiResponse[DueReviewListResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            items = [
                DueReviewResponse.from_due_item(item)
                for item in list_due_reviews(session, due_on=date_value)
            ]
    except (KnowledgeError, MasteryServiceError, ReviewError) as exc:
        raise _api_review_error(exc) from exc
    return api_response(
        DueReviewListResponse(date=date_value, items=items, total=len(items)),
        request,
    )


@router.post("/recalculate", response_model=ApiResponse[ReviewRecalculateResponse])
def recalculate_reviews(request: Request) -> ApiResponse[ReviewRecalculateResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            schedules = recalculate_review_schedules(session)
            items = [ReviewScheduleResponse.from_model(schedule) for schedule in schedules]
    except (KnowledgeError, MasteryServiceError, ReviewError) as exc:
        raise _api_review_error(exc) from exc
    return api_response(ReviewRecalculateResponse(items=items, total=len(items)), request)


@router.post("/{schedule_id}/results", response_model=ApiResponse[ReviewResultSubmitResponse])
def submit_result(
    request: Request,
    schedule_id: str,
    payload: ReviewResultCreate,
    idempotency_key: IdempotencyKey = None,
) -> ApiResponse[ReviewResultSubmitResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            submission = submit_review_result(
                session,
                schedule_id,
                idempotency_key=idempotency_key,
                request_id=get_request_id(request),
                **payload.model_dump(),
            )
            response = ReviewResultSubmitResponse.from_submission(submission)
    except (KnowledgeError, MasteryServiceError, ReviewError) as exc:
        raise _api_review_error(exc) from exc
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_review_error(exc: KnowledgeError | MasteryServiceError | ReviewError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
