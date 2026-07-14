from fastapi import APIRouter, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.insights.service import (
    get_error_analytics,
    get_full_graph,
    get_goal_risk_analytics,
    get_mastery_analytics,
    get_overview,
    get_time_analytics,
    get_weak_graph,
)
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.insights import (
    AnalyticsErrorsResponse,
    AnalyticsGoalRiskResponse,
    AnalyticsMasteryResponse,
    AnalyticsOverviewResponse,
    AnalyticsTimeResponse,
    GraphResponse,
    WeakGraphResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["insights"])


@router.get("/graph/full", response_model=ApiResponse[GraphResponse])
def graph_full(request: Request) -> ApiResponse[GraphResponse]:
    with _session_factory()() as session:
        response = get_full_graph(session)
    return api_response(response, request)


@router.get("/graph/weak", response_model=ApiResponse[WeakGraphResponse])
def graph_weak(request: Request) -> ApiResponse[WeakGraphResponse]:
    with _session_factory()() as session:
        response = get_weak_graph(session)
    return api_response(response, request)


@router.get("/analytics/overview", response_model=ApiResponse[AnalyticsOverviewResponse])
def analytics_overview(request: Request) -> ApiResponse[AnalyticsOverviewResponse]:
    with _session_factory()() as session:
        response = get_overview(session)
    return api_response(response, request)


@router.get("/analytics/time", response_model=ApiResponse[AnalyticsTimeResponse])
def analytics_time(request: Request) -> ApiResponse[AnalyticsTimeResponse]:
    with _session_factory()() as session:
        response = get_time_analytics(session)
    return api_response(response, request)


@router.get("/analytics/errors", response_model=ApiResponse[AnalyticsErrorsResponse])
def analytics_errors(request: Request) -> ApiResponse[AnalyticsErrorsResponse]:
    with _session_factory()() as session:
        response = get_error_analytics(session)
    return api_response(response, request)


@router.get("/analytics/mastery", response_model=ApiResponse[AnalyticsMasteryResponse])
def analytics_mastery(request: Request) -> ApiResponse[AnalyticsMasteryResponse]:
    with _session_factory()() as session:
        response = get_mastery_analytics(session)
    return api_response(response, request)


@router.get("/analytics/goal-risk", response_model=ApiResponse[AnalyticsGoalRiskResponse])
def analytics_goal_risk(request: Request) -> ApiResponse[AnalyticsGoalRiskResponse]:
    with _session_factory()() as session:
        response = get_goal_risk_analytics(session)
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)
