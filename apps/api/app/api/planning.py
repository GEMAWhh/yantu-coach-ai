from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_session_factory
from app.errors import ApiError
from app.planning.service import (
    PlanningError,
    create_goal,
    create_task,
    get_goal,
    get_goal_tree,
    get_task,
    list_tasks,
    set_task_status,
    soft_delete_goal,
    submit_task_result,
    update_goal,
    update_task,
)
from app.request_context import get_request_id
from app.responses import api_response
from app.schemas.common import ApiResponse
from app.schemas.planning import (
    GoalCreate,
    GoalResponse,
    GoalTreeListResponse,
    GoalTreeResponse,
    GoalUpdate,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskResultCreate,
    TaskResultResponse,
    TaskResultSubmitResponse,
    TaskStatus,
    TaskUpdate,
    TodayResponse,
)
from app.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["planning"])
IfMatch = Annotated[str | None, Header(alias="If-Match")]
IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key")]


@router.get("/today", response_model=ApiResponse[TodayResponse])
def today(
    request: Request,
    date_value: Annotated[date, Query(alias="date")],
) -> ApiResponse[TodayResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        tasks = list_tasks(session, planned_date=date_value)
        task_items = [TaskResponse.from_model(task) for task in tasks]
    return api_response(
        TodayResponse(
            date=date_value,
            tasks=task_items,
            total_tasks=len(task_items),
            estimated_minutes=sum(task.estimated_minutes for task in tasks),
        ),
        request,
    )


@router.post("/goals", response_model=ApiResponse[GoalResponse])
def create_goal_endpoint(
    request: Request,
    payload: GoalCreate,
) -> ApiResponse[GoalResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            goal = create_goal(session, **payload.model_dump())
            response = GoalResponse.from_model(goal)
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.get("/goals/tree", response_model=ApiResponse[GoalTreeListResponse])
def goals_tree(
    request: Request,
    root_goal_id: str | None = Query(default=None),
) -> ApiResponse[GoalTreeListResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            items = [
                GoalTreeResponse.from_tree(tree) for tree in get_goal_tree(session, root_goal_id)
            ]
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(GoalTreeListResponse(items=items, total=len(items)), request)


@router.get("/goals/{goal_id}", response_model=ApiResponse[GoalResponse])
def get_goal_endpoint(request: Request, goal_id: str) -> ApiResponse[GoalResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = GoalResponse.from_model(get_goal(session, goal_id))
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.patch("/goals/{goal_id}", response_model=ApiResponse[GoalResponse])
def update_goal_endpoint(
    request: Request,
    goal_id: str,
    payload: GoalUpdate,
    if_match: IfMatch = None,
) -> ApiResponse[GoalResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            goal = update_goal(
                session,
                goal_id,
                expected_version=if_match,
                **payload.model_dump(exclude_unset=True),
            )
            response = GoalResponse.from_model(goal)
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.delete("/goals/{goal_id}", response_model=ApiResponse[GoalResponse])
def delete_goal_endpoint(request: Request, goal_id: str) -> ApiResponse[GoalResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            response = GoalResponse.from_model(soft_delete_goal(session, goal_id))
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.post("/tasks", response_model=ApiResponse[TaskResponse])
def create_task_endpoint(
    request: Request,
    payload: TaskCreate,
) -> ApiResponse[TaskResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            task = create_task(session, **payload.model_dump())
            response = TaskResponse.from_model(task)
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.get("/tasks", response_model=ApiResponse[TaskListResponse])
def list_tasks_endpoint(
    request: Request,
    planned_date: Annotated[date | None, Query()] = None,
) -> ApiResponse[TaskListResponse]:
    session_factory = _session_factory()
    with session_factory() as session:
        tasks = list_tasks(session, planned_date=planned_date)
        items = [TaskResponse.from_model(task) for task in tasks]
    return api_response(TaskListResponse(items=items, total=len(items)), request)


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def get_task_endpoint(request: Request, task_id: str) -> ApiResponse[TaskResponse]:
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            response = TaskResponse.from_model(get_task(session, task_id))
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.patch("/tasks/{task_id}", response_model=ApiResponse[TaskResponse])
def update_task_endpoint(
    request: Request,
    task_id: str,
    payload: TaskUpdate,
    if_match: IfMatch = None,
) -> ApiResponse[TaskResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            task = update_task(
                session,
                task_id,
                expected_version=if_match,
                **payload.model_dump(exclude_unset=True),
            )
            response = TaskResponse.from_model(task)
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


@router.post("/tasks/{task_id}/start", response_model=ApiResponse[TaskResponse])
def start_task(
    request: Request,
    task_id: str,
    if_match: IfMatch = None,
) -> ApiResponse[TaskResponse]:
    return _set_task_status_response(request, task_id, status="in_progress", if_match=if_match)


@router.post("/tasks/{task_id}/skip", response_model=ApiResponse[TaskResponse])
def skip_task(
    request: Request,
    task_id: str,
    if_match: IfMatch = None,
) -> ApiResponse[TaskResponse]:
    return _set_task_status_response(request, task_id, status="skipped", if_match=if_match)


@router.post("/tasks/{task_id}/withdraw", response_model=ApiResponse[TaskResponse])
def withdraw_task(
    request: Request,
    task_id: str,
    if_match: IfMatch = None,
) -> ApiResponse[TaskResponse]:
    return _set_task_status_response(request, task_id, status="withdrawn", if_match=if_match)


@router.post("/tasks/{task_id}/results", response_model=ApiResponse[TaskResultSubmitResponse])
def submit_result(
    request: Request,
    task_id: str,
    payload: TaskResultCreate,
    idempotency_key: IdempotencyKey = None,
) -> ApiResponse[TaskResultSubmitResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            submitted = submit_task_result(
                session,
                task_id,
                idempotency_key=idempotency_key,
                request_id=get_request_id(request),
                **payload.model_dump(),
            )
            response = TaskResultSubmitResponse(
                result=TaskResultResponse.from_model(submitted.result),
                created=submitted.created,
            )
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


def _set_task_status_response(
    request: Request,
    task_id: str,
    *,
    status: str,
    if_match: str | None,
) -> ApiResponse[TaskResponse]:
    session_factory = _session_factory()
    try:
        with session_factory.begin() as session:
            task = set_task_status(
                session,
                task_id,
                status=cast(TaskStatus, status),
                expected_version=if_match,
            )
            response = TaskResponse.from_model(task)
    except PlanningError as exc:
        raise _api_planning_error(exc) from exc
    return api_response(response, request)


def _session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    return get_session_factory(settings.database_url)


def _api_planning_error(exc: PlanningError) -> ApiError:
    return ApiError(
        status_code=exc.status_code,
        code=exc.code,
        message=str(exc),
        details=exc.details,
    )
