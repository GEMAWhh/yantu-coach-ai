from fastapi import APIRouter, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.time_calibration import (
    TimeAdjustmentListResponse,
    TimeAdjustmentResponse,
    TimeCoefficientListResponse,
    TimeCoefficientResponse,
)
from app.settings import get_settings
from app.time_calibration.service import list_time_adjustments, list_time_coefficients

router = APIRouter(prefix="/api/v1/time-calibration", tags=["time-calibration"])


@router.get("/coefficients", response_model=ApiResponse[TimeCoefficientListResponse])
def coefficients(request: Request) -> ApiResponse[TimeCoefficientListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [
            TimeCoefficientResponse.from_model(item) for item in list_time_coefficients(session)
        ]
    return api_response(TimeCoefficientListResponse(items=items, total=len(items)), request)


@router.get("/adjustments", response_model=ApiResponse[TimeAdjustmentListResponse])
def adjustments(request: Request) -> ApiResponse[TimeAdjustmentListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        items = [TimeAdjustmentResponse.from_model(item) for item in list_time_adjustments(session)]
    return api_response(TimeAdjustmentListResponse(items=items, total=len(items)), request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)
