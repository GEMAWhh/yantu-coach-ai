from dataclasses import dataclass, field
from datetime import date, datetime
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.models.base import utc_now
from app.models.knowledge import KnowledgeNode
from app.models.planning import Goal, Task, TaskResult
from app.services.audit import write_audit_event

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
    if task.goal_id is not None:
        _recalculate_goal_progress(session, task.goal_id)
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


def _recalculate_goal_progress(session: Session, goal_id: str) -> None:
    goal = get_goal(session, goal_id)
    tasks = list(
        session.scalars(
            select(Task).where(Task.goal_id == goal.id, Task.is_deleted.is_(False))
        ).all()
    )
    if not tasks:
        goal.progress = 0
        goal.actual_minutes = 0
        session.flush()
        return
    task_ids = [task.id for task in tasks]
    results = list(
        session.scalars(select(TaskResult).where(TaskResult.task_id.in_(task_ids))).all()
    )
    actual_minutes = sum(result.actual_minutes for result in results)
    completion_by_task = {task.id: 0 for task in tasks}
    for result in results:
        completion_by_task[result.task_id] = max(
            completion_by_task[result.task_id],
            result.completion_ratio,
        )
    goal.actual_minutes = actual_minutes
    goal.progress = round(sum(completion_by_task.values()) / len(tasks))
    session.flush()


def latest_task_result(session: Session, task_id: str) -> TaskResult | None:
    return session.scalar(
        select(TaskResult)
        .where(TaskResult.task_id == task_id)
        .order_by(literal_column("rowid").desc())
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
