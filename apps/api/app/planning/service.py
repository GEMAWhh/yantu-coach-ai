from dataclasses import dataclass, field
from datetime import date, datetime
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.knowledge import KnowledgeNode
from app.models.planning import Goal, GoalHistoryEvent, Task, TaskResult
from app.services.audit import write_audit_event
from app.time_calibration.service import update_time_coefficient_from_task_result

GoalLevel = Literal["semester", "quarter", "month", "week", "day"]
GoalStatus = Literal["draft", "active", "completed", "delayed", "archived", "cancelled"]
TaskStatus = Literal["pending", "in_progress", "completed", "skipped", "withdrawn"]
TaskResultType = Literal["completed", "partial", "wrong", "unknown"]

GOAL_LEVELS = {"semester", "quarter", "month", "week", "day"}
GOAL_STATUSES = {"draft", "active", "completed", "delayed", "archived", "cancelled"}
TASK_STATUSES = {"pending", "in_progress", "completed", "skipped", "withdrawn"}
TASK_RESULT_TYPES = {"completed", "partial", "wrong", "unknown"}


class PlanningError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "PLANNING_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class GoalTreeNode:
    goal: Goal
    children: list["GoalTreeNode"] = field(default_factory=list)


@dataclass(frozen=True)
class TaskResultSubmission:
    result: TaskResult
    created: bool


@dataclass(frozen=True)
class GoalRecalculation:
    root: Goal
    events: list[GoalHistoryEvent]


def create_goal(
    session: Session,
    *,
    level: GoalLevel,
    title: str,
    parent_id: str | None = None,
    subject_id: str | None = None,
    description: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    estimated_minutes: int = 0,
    completion_standard: str | None = None,
    risk_status: str = "normal",
    status: GoalStatus = "active",
    adjustment_reason: str | None = None,
    created_by: str = "system",
) -> Goal:
    _validate_goal_level(level)
    _validate_goal_status(status)
    _validate_non_negative("estimated_minutes", estimated_minutes)
    parent = get_goal(session, parent_id) if parent_id is not None else None
    goal = Goal(
        id=str(uuid4()),
        parent_id=parent.id if parent is not None else None,
        level=level,
        subject_id=subject_id,
        title=title,
        description=description,
        start_date=start_date,
        end_date=end_date,
        estimated_minutes=estimated_minutes,
        actual_minutes=0,
        completion_standard=completion_standard,
        progress=0,
        risk_status=risk_status,
        status=status,
        adjustment_reason=adjustment_reason,
        created_by=created_by,
    )
    session.add(goal)
    session.flush()
    return goal


def get_goal(session: Session, goal_id: str, *, include_deleted: bool = False) -> Goal:
    goal = session.get(Goal, goal_id)
    if goal is None or (goal.is_deleted and not include_deleted):
        raise PlanningError(
            "goal not found",
            code="GOAL_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"goal_id": goal_id},
        )
    return goal


def list_goals(
    session: Session,
    *,
    parent_id: str | None = None,
    include_deleted: bool = False,
) -> list[Goal]:
    statement = select(Goal)
    if parent_id is not None:
        statement = statement.where(Goal.parent_id == parent_id)
    if not include_deleted:
        statement = statement.where(Goal.is_deleted.is_(False))
    return list(session.scalars(statement.order_by(Goal.start_date, Goal.created_at)).all())


def get_goal_tree(session: Session, root_goal_id: str | None = None) -> list[GoalTreeNode]:
    goals = list_goals(session)
    if root_goal_id is not None:
        root = get_goal(session, root_goal_id)
        root_ids = {root.id}
    else:
        root_ids = {goal.id for goal in goals if goal.parent_id is None}
    children_by_parent: dict[str | None, list[Goal]] = {}
    for goal in goals:
        children_by_parent.setdefault(goal.parent_id, []).append(goal)

    def build(goal: Goal) -> GoalTreeNode:
        return GoalTreeNode(
            goal=goal,
            children=[build(child) for child in children_by_parent.get(goal.id, [])],
        )

    return [build(goal) for goal in goals if goal.id in root_ids]


def list_goal_history(session: Session, goal_id: str) -> list[GoalHistoryEvent]:
    goal = get_goal(session, goal_id)
    return list(
        session.scalars(
            select(GoalHistoryEvent)
            .where(GoalHistoryEvent.goal_id == goal.id)
            .order_by(GoalHistoryEvent.created_at, GoalHistoryEvent.id)
        ).all()
    )


def recalculate_goal_tree(
    session: Session,
    goal_id: str,
    *,
    as_of: date | None = None,
    reason: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    request_id: str | None = None,
    created_by: str = "system",
    force_root_history: bool = True,
) -> GoalRecalculation:
    root = get_goal(session, goal_id)
    events = _recalculate_goal_and_descendants(
        session,
        root,
        as_of=as_of or utc_now().date(),
        reason=reason,
        source_type=source_type,
        source_id=source_id,
        request_id=request_id,
        created_by=created_by,
        force_history=force_root_history,
    )
    session.flush()
    return GoalRecalculation(root=root, events=events)


def update_goal(
    session: Session,
    goal_id: str,
    *,
    expected_version: str | None = None,
    title: str | None = None,
    description: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    estimated_minutes: int | None = None,
    completion_standard: str | None = None,
    risk_status: str | None = None,
    status: GoalStatus | None = None,
    adjustment_reason: str | None = None,
) -> Goal:
    goal = get_goal(session, goal_id)
    _check_version(goal.version, expected_version)
    if title is not None:
        goal.title = title
    if description is not None:
        goal.description = description
    if start_date is not None:
        goal.start_date = start_date
    if end_date is not None:
        goal.end_date = end_date
    if estimated_minutes is not None:
        _validate_non_negative("estimated_minutes", estimated_minutes)
        goal.estimated_minutes = estimated_minutes
    if completion_standard is not None:
        goal.completion_standard = completion_standard
    if risk_status is not None:
        goal.risk_status = risk_status
    if status is not None:
        _validate_goal_status(status)
        goal.status = status
    if adjustment_reason is not None:
        goal.adjustment_reason = adjustment_reason
    session.flush()
    return goal


def soft_delete_goal(session: Session, goal_id: str) -> Goal:
    goal = get_goal(session, goal_id)
    deleted_at = utc_now()
    goal_ids = _collect_goal_descendant_ids(session, goal.id)
    goals = session.scalars(select(Goal).where(Goal.id.in_(goal_ids))).all()
    for item in goals:
        item.is_deleted = True
        item.deleted_at = deleted_at
        item.status = "archived"
    tasks = session.scalars(select(Task).where(Task.goal_id.in_(goal_ids))).all()
    for task in tasks:
        task.is_deleted = True
        task.deleted_at = deleted_at
        task.status = "withdrawn"
    session.flush()
    return goal


def create_task(
    session: Session,
    *,
    title: str,
    planned_date: date,
    estimated_minutes: int,
    source_type: str,
    goal_id: str | None = None,
    subject_id: str | None = None,
    knowledge_node_id: str | None = None,
    wrong_record_id: str | None = None,
    review_schedule_id: str | None = None,
    task_type: str = "study",
    priority: str = "normal",
    source_id: str | None = None,
    difficulty: str | None = None,
    cognitive_load: str | None = None,
    current_stage: int | None = None,
    target_stage: int | None = None,
    reason: str | None = None,
    completion_standard: str | None = None,
    prerequisite_status: str = "unknown",
    status: TaskStatus = "pending",
    created_by: str = "system",
) -> Task:
    _validate_non_negative("estimated_minutes", estimated_minutes)
    _validate_task_status(status)
    if goal_id is not None:
        get_goal(session, goal_id)
    if knowledge_node_id is not None and session.get(KnowledgeNode, knowledge_node_id) is None:
        raise PlanningError(
            "knowledge node not found",
            code="KNOWLEDGE_NODE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"knowledge_node_id": knowledge_node_id},
        )
    task = Task(
        id=str(uuid4()),
        goal_id=goal_id,
        subject_id=subject_id,
        knowledge_node_id=knowledge_node_id,
        wrong_record_id=wrong_record_id,
        review_schedule_id=review_schedule_id,
        title=title,
        task_type=task_type,
        priority=priority,
        source_type=source_type,
        source_id=source_id,
        planned_date=planned_date,
        estimated_minutes=estimated_minutes,
        difficulty=difficulty,
        cognitive_load=cognitive_load,
        current_stage=current_stage,
        target_stage=target_stage,
        reason=reason,
        completion_standard=completion_standard,
        prerequisite_status=prerequisite_status,
        status=status,
        created_by=created_by,
    )
    session.add(task)
    session.flush()
    return task


def get_task(session: Session, task_id: str, *, include_deleted: bool = False) -> Task:
    task = session.get(Task, task_id)
    if task is None or (task.is_deleted and not include_deleted):
        raise PlanningError(
            "task not found",
            code="TASK_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"task_id": task_id},
        )
    return task


def list_tasks(
    session: Session,
    *,
    planned_date: date | None = None,
    include_deleted: bool = False,
) -> list[Task]:
    statement = select(Task)
    if planned_date is not None:
        statement = statement.where(Task.planned_date == planned_date)
    if not include_deleted:
        statement = statement.where(Task.is_deleted.is_(False))
    return list(session.scalars(statement.order_by(Task.planned_date, Task.created_at)).all())


def update_task(
    session: Session,
    task_id: str,
    *,
    expected_version: str | None = None,
    title: str | None = None,
    planned_date: date | None = None,
    estimated_minutes: int | None = None,
    priority: str | None = None,
    reason: str | None = None,
    completion_standard: str | None = None,
    prerequisite_status: str | None = None,
    status: TaskStatus | None = None,
) -> Task:
    task = get_task(session, task_id)
    _check_version(task.version, expected_version)
    if title is not None:
        task.title = title
    if planned_date is not None:
        task.planned_date = planned_date
    if estimated_minutes is not None:
        _validate_non_negative("estimated_minutes", estimated_minutes)
        task.estimated_minutes = estimated_minutes
    if priority is not None:
        task.priority = priority
    if reason is not None:
        task.reason = reason
    if completion_standard is not None:
        task.completion_standard = completion_standard
    if prerequisite_status is not None:
        task.prerequisite_status = prerequisite_status
    if status is not None:
        _validate_task_status(status)
        task.status = status
    session.flush()
    return task


def soft_delete_task(session: Session, task_id: str) -> Task:
    task = get_task(session, task_id)
    if task.status != "pending":
        raise PlanningError(
            "only pending tasks can be deleted",
            code="TASK_DELETE_NOT_ALLOWED",
            status_code=HTTPStatus.CONFLICT,
            details={"task_id": task_id, "status": task.status},
        )
    has_result = session.scalar(select(TaskResult.id).where(TaskResult.task_id == task.id).limit(1))
    if has_result is not None:
        raise PlanningError(
            "tasks with results cannot be deleted",
            code="TASK_DELETE_NOT_ALLOWED",
            status_code=HTTPStatus.CONFLICT,
            details={"task_id": task_id, "reason": "result_exists"},
        )
    task.is_deleted = True
    task.deleted_at = utc_now()
    task.status = "withdrawn"
    session.flush()
    return task


def set_task_status(
    session: Session,
    task_id: str,
    *,
    status: TaskStatus,
    expected_version: str | None = None,
) -> Task:
    return update_task(session, task_id, expected_version=expected_version, status=status)


def submit_task_result(
    session: Session,
    task_id: str,
    *,
    result_type: TaskResultType,
    completion_ratio: int,
    actual_minutes: int,
    question_count: int | None = None,
    correct_count: int | None = None,
    accuracy: int | None = None,
    confidence: int | None = None,
    hint_level: int | None = None,
    focus_level: int | None = None,
    difficulty_rating: int | None = None,
    problem_description: str | None = None,
    confirmed_at: datetime | None = None,
    idempotency_key: str | None = None,
    request_id: str | None = None,
    created_by: str = "system",
) -> TaskResultSubmission:
    task = get_task(session, task_id)
    _validate_task_result(
        result_type=result_type,
        completion_ratio=completion_ratio,
        actual_minutes=actual_minutes,
        question_count=question_count,
        correct_count=correct_count,
        accuracy=accuracy,
        confidence=confidence,
    )
    if idempotency_key:
        existing = session.scalar(
            select(TaskResult).where(
                TaskResult.task_id == task.id,
                TaskResult.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return TaskResultSubmission(result=existing, created=False)
    result = TaskResult(
        id=str(uuid4()),
        task_id=task.id,
        idempotency_key=idempotency_key,
        result_type=result_type,
        completion_ratio=completion_ratio,
        actual_minutes=actual_minutes,
        question_count=question_count,
        correct_count=correct_count,
        accuracy=accuracy,
        confidence=confidence,
        hint_level=hint_level,
        focus_level=focus_level,
        difficulty_rating=difficulty_rating,
        problem_description=problem_description,
        confirmed_at=confirmed_at or utc_now(),
        request_id=request_id,
        created_by=created_by,
    )
    session.add(result)
    session.flush()
    update_time_coefficient_from_task_result(session, result, request_id=request_id)
    if task.goal_id is not None:
        _recalculate_goal_progress(
            session,
            task.goal_id,
            as_of=result.confirmed_at.date(),
            source_type="task_result",
            source_id=result.id,
            request_id=request_id,
        )
    write_audit_event(
        session,
        event_type="task_result.submitted",
        actor_type=created_by,
        object_type="task_result",
        object_id=result.id,
        after_json={
            "task_id": task.id,
            "result_type": result_type,
            "completion_ratio": completion_ratio,
            "actual_minutes": actual_minutes,
            "accuracy": accuracy,
        },
        reason="task result submitted without changing mastery directly",
        request_id=request_id,
    )
    return TaskResultSubmission(result=result, created=True)


def _recalculate_goal_progress(
    session: Session,
    goal_id: str,
    *,
    as_of: date | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    request_id: str | None = None,
) -> None:
    goal = get_goal(session, goal_id)
    root = _root_goal(session, goal)
    recalculate_goal_tree(
        session,
        root.id,
        as_of=as_of,
        reason="task result changed goal progress",
        source_type=source_type,
        source_id=source_id,
        request_id=request_id,
        force_root_history=False,
    )


def _recalculate_goal_and_descendants(
    session: Session,
    goal: Goal,
    *,
    as_of: date,
    reason: str | None,
    source_type: str | None,
    source_id: str | None,
    request_id: str | None,
    created_by: str,
    force_history: bool,
) -> list[GoalHistoryEvent]:
    events: list[GoalHistoryEvent] = []
    children = list(
        session.scalars(
            select(Goal).where(Goal.parent_id == goal.id, Goal.is_deleted.is_(False))
        ).all()
    )
    for child in children:
        events.extend(
            _recalculate_goal_and_descendants(
                session,
                child,
                as_of=as_of,
                reason=reason,
                source_type=source_type,
                source_id=source_id,
                request_id=request_id,
                created_by=created_by,
                force_history=False,
            )
        )

    previous = _goal_state(goal)
    progress, actual_minutes, completion_by_task, tasks = _computed_goal_progress(
        session, goal, children
    )
    risk_status = _computed_goal_risk(
        goal,
        children,
        progress=progress,
        completion_by_task=completion_by_task,
        tasks=tasks,
        as_of=as_of,
    )
    status = _computed_goal_status(goal, progress, risk_status)

    goal.progress = progress
    goal.actual_minutes = actual_minutes
    goal.risk_status = risk_status
    goal.status = status
    changed = previous != _goal_state(goal)
    if changed or force_history:
        event = GoalHistoryEvent(
            id=str(uuid4()),
            goal_id=goal.id,
            event_type="goal.recalculated",
            previous_progress=previous["progress"],
            new_progress=goal.progress,
            previous_actual_minutes=previous["actual_minutes"],
            new_actual_minutes=goal.actual_minutes,
            previous_risk_status=previous["risk_status"],
            new_risk_status=goal.risk_status,
            previous_status=previous["status"],
            new_status=goal.status,
            reason=reason or "goal recalculated from child goals and task results",
            source_type=source_type,
            source_id=source_id,
            request_id=request_id,
            created_by=created_by,
        )
        session.add(event)
        events.append(event)
    return events


def _computed_goal_progress(
    session: Session,
    goal: Goal,
    children: list[Goal],
) -> tuple[int, int, dict[str, int], list[Task]]:
    tasks = list(
        session.scalars(
            select(Task).where(Task.goal_id == goal.id, Task.is_deleted.is_(False))
        ).all()
    )
    task_ids = [task.id for task in tasks]
    results = (
        list(session.scalars(select(TaskResult).where(TaskResult.task_id.in_(task_ids))).all())
        if task_ids
        else []
    )
    completion_by_task = {task.id: 0 for task in tasks}
    for result in results:
        completion_by_task[result.task_id] = max(
            completion_by_task[result.task_id],
            result.completion_ratio,
        )
    progress_parts = list(completion_by_task.values()) + [child.progress for child in children]
    progress = round(sum(progress_parts) / len(progress_parts)) if progress_parts else 0
    actual_minutes = sum(result.actual_minutes for result in results) + sum(
        child.actual_minutes for child in children
    )
    return progress, actual_minutes, completion_by_task, tasks


def _computed_goal_risk(
    goal: Goal,
    children: list[Goal],
    *,
    progress: int,
    completion_by_task: dict[str, int],
    tasks: list[Task],
    as_of: date,
) -> str:
    if progress >= 100:
        return "normal"
    if goal.end_date is not None and goal.end_date < as_of:
        return "high"
    if any(child.risk_status == "high" for child in children):
        return "high"
    if any(child.risk_status == "at_risk" for child in children):
        return "at_risk"
    if any(
        task.planned_date < as_of
        and completion_by_task.get(task.id, 0) < 100
        and task.status not in {"completed", "skipped", "withdrawn"}
        for task in tasks
    ):
        return "at_risk"
    return "normal"


def _computed_goal_status(goal: Goal, progress: int, risk_status: str) -> str:
    if goal.status in {"archived", "cancelled", "draft"}:
        return goal.status
    if progress >= 100:
        return "completed"
    if risk_status == "high" and goal.status == "active":
        return "delayed"
    if goal.status == "completed" and progress < 100:
        return "active"
    return goal.status


def _goal_state(goal: Goal) -> dict[str, int | str]:
    return {
        "progress": goal.progress,
        "actual_minutes": goal.actual_minutes,
        "risk_status": goal.risk_status,
        "status": goal.status,
    }


def _root_goal(session: Session, goal: Goal) -> Goal:
    current = goal
    while current.parent_id is not None:
        parent = session.get(Goal, current.parent_id)
        if parent is None or parent.is_deleted:
            break
        current = parent
    return current


def latest_task_result(session: Session, task_id: str) -> TaskResult | None:
    return session.scalar(
        select(TaskResult)
        .where(TaskResult.task_id == task_id)
        .order_by(TaskResult.created_at.desc(), TaskResult.id.desc())
    )


def _collect_goal_descendant_ids(session: Session, root_goal_id: str) -> list[str]:
    goals = list_goals(session)
    children_by_parent: dict[str | None, list[str]] = {}
    for goal in goals:
        children_by_parent.setdefault(goal.parent_id, []).append(goal.id)
    collected: list[str] = []
    stack = [root_goal_id]
    while stack:
        current = stack.pop()
        if current in collected:
            continue
        collected.append(current)
        stack.extend(children_by_parent.get(current, []))
    return collected


def _check_version(current_version: int, expected_version: str | None) -> None:
    if expected_version is None:
        return
    if expected_version.strip() != str(current_version):
        raise PlanningError(
            "Resource version conflict",
            code="VERSION_CONFLICT",
            status_code=HTTPStatus.CONFLICT,
            details={"expected": str(current_version), "received": expected_version},
        )


def _validate_goal_level(level: str) -> None:
    if level not in GOAL_LEVELS:
        raise PlanningError(
            "unsupported goal level",
            code="GOAL_LEVEL_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"level": level},
        )


def _validate_goal_status(status: str) -> None:
    if status not in GOAL_STATUSES:
        raise PlanningError(
            "unsupported goal status",
            code="GOAL_STATUS_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"status": status},
        )


def _validate_task_status(status: str) -> None:
    if status not in TASK_STATUSES:
        raise PlanningError(
            "unsupported task status",
            code="TASK_STATUS_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"status": status},
        )


def _validate_task_result(
    *,
    result_type: str,
    completion_ratio: int,
    actual_minutes: int,
    question_count: int | None,
    correct_count: int | None,
    accuracy: int | None,
    confidence: int | None,
) -> None:
    if result_type not in TASK_RESULT_TYPES:
        raise PlanningError(
            "unsupported task result type",
            code="TASK_RESULT_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"result_type": result_type},
        )
    _validate_range("completion_ratio", completion_ratio, minimum=0, maximum=100)
    _validate_non_negative("actual_minutes", actual_minutes)
    for field_name, value in {
        "question_count": question_count,
        "correct_count": correct_count,
    }.items():
        if value is not None:
            _validate_non_negative(field_name, value)
    for field_name, value in {"accuracy": accuracy, "confidence": confidence}.items():
        if value is not None:
            _validate_range(field_name, value, minimum=0, maximum=100)


def _validate_non_negative(field_name: str, value: int) -> None:
    if value < 0:
        raise PlanningError(
            "numeric planning fields must not be negative",
            code="PLANNING_VALUE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"field": field_name, "value": value},
        )


def _validate_range(field_name: str, value: int, *, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise PlanningError(
            "numeric planning fields are outside allowed range",
            code="PLANNING_VALUE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"field": field_name, "value": value, "minimum": minimum, "maximum": maximum},
        )
