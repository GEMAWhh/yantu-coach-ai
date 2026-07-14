from dataclasses import dataclass, replace
from http import HTTPStatus
from math import ceil
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.planning import Task, TaskResult
from app.models.time_calibration import TimeAdjustment, TimeCoefficient
from app.planning.engine import PlanningCandidate

TIME_CALIBRATION_RULE_VERSION = "time-calibration-v1.0.0"
DEFAULT_SUBJECT_ID = "global"
DEFAULT_DIFFICULTY = "default"
DEFAULT_COEFFICIENT = 1.0
MIN_COEFFICIENT = 0.6
MAX_COEFFICIENT = 1.8
SMOOTHING_ALPHA = 0.3
MIN_APPLIED_RATIO = 0.5
MAX_APPLIED_RATIO = 2.0
MIN_ACCEPTED_RATIO = 0.25
MAX_ACCEPTED_RATIO = 3.0
OVERTIME_RATIO = 1.25
SPLIT_STREAK_THRESHOLD = 2


class TimeCalibrationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "TIME_CALIBRATION_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class TimeCalibrationUpdate:
    coefficient: TimeCoefficient
    adjustment: TimeAdjustment
    created: bool


def update_time_coefficient_from_task_result(
    session: Session,
    task_result: TaskResult,
    *,
    request_id: str | None = None,
) -> TimeCalibrationUpdate:
    existing = session.scalar(
        select(TimeAdjustment).where(TimeAdjustment.task_result_id == task_result.id)
    )
    task = _get_task(session, task_result.task_id)
    coefficient = _get_or_create_coefficient(
        session,
        subject_id=_scope_subject_id(task.subject_id),
        task_type=task.task_type,
        difficulty=_scope_difficulty(task.difficulty),
    )
    if existing is not None:
        return TimeCalibrationUpdate(
            coefficient=coefficient,
            adjustment=existing,
            created=False,
        )

    previous = coefficient.coefficient
    raw_ratio, applied_ratio, ignore_reason = _ratio_for_update(
        estimated_minutes=task.estimated_minutes,
        actual_minutes=task_result.actual_minutes,
    )
    ignored = ignore_reason is not None
    overtime = raw_ratio is not None and raw_ratio >= OVERTIME_RATIO
    if ignored:
        new_coefficient = previous
        suggested_split = coefficient.overtime_streak >= SPLIT_STREAK_THRESHOLD
    else:
        assert applied_ratio is not None
        new_coefficient = _clamp_coefficient(
            (previous * (1 - SMOOTHING_ALPHA)) + (applied_ratio * SMOOTHING_ALPHA)
        )
        coefficient.coefficient = new_coefficient
        coefficient.sample_count += 1
        coefficient.overtime_streak = coefficient.overtime_streak + 1 if overtime else 0
        coefficient.last_ratio = raw_ratio
        coefficient.last_estimated_minutes = task.estimated_minutes
        coefficient.last_actual_minutes = task_result.actual_minutes
        coefficient.last_task_result_id = task_result.id
        coefficient.rationale_json = {
            "last_task_id": task.id,
            "last_task_result_id": task_result.id,
            "raw_ratio": raw_ratio,
            "applied_ratio": applied_ratio,
            "alpha": SMOOTHING_ALPHA,
        }
        suggested_split = coefficient.overtime_streak >= SPLIT_STREAK_THRESHOLD

    adjustment = TimeAdjustment(
        id=str(uuid4()),
        coefficient_id=coefficient.id,
        task_id=task.id,
        task_result_id=task_result.id,
        subject_id=coefficient.subject_id,
        task_type=coefficient.task_type,
        difficulty=coefficient.difficulty,
        estimated_minutes=task.estimated_minutes,
        actual_minutes=task_result.actual_minutes,
        raw_ratio=raw_ratio,
        applied_ratio=applied_ratio,
        previous_coefficient=previous,
        new_coefficient=new_coefficient,
        ignored=ignored,
        ignore_reason=ignore_reason,
        overtime=overtime,
        suggested_split=suggested_split,
        rule_version=TIME_CALIBRATION_RULE_VERSION,
        occurred_at=task_result.confirmed_at,
        request_id=request_id,
    )
    session.add(adjustment)
    session.flush()
    return TimeCalibrationUpdate(coefficient=coefficient, adjustment=adjustment, created=True)


def apply_time_calibration_to_candidates(
    session: Session,
    candidates: list[PlanningCandidate],
) -> list[PlanningCandidate]:
    calibrated = []
    for candidate in candidates:
        coefficient = get_time_coefficient(
            session,
            subject_id=candidate.subject_id,
            task_type=candidate.task_type,
            difficulty=candidate.difficulty,
        )
        if coefficient is None:
            calibrated.append(candidate)
            continue
        calibrated_minutes = max(1, ceil(candidate.estimated_minutes * coefficient.coefficient))
        calibrated.append(
            replace(
                candidate,
                estimated_minutes=calibrated_minutes,
                overtime_count=max(candidate.overtime_count, coefficient.overtime_streak),
            )
        )
    return calibrated


def get_time_coefficient(
    session: Session,
    *,
    subject_id: str | None,
    task_type: str,
    difficulty: str | None = None,
) -> TimeCoefficient | None:
    return session.scalar(
        select(TimeCoefficient).where(
            TimeCoefficient.subject_id == _scope_subject_id(subject_id),
            TimeCoefficient.task_type == task_type,
            TimeCoefficient.difficulty == _scope_difficulty(difficulty),
        )
    )


def list_time_coefficients(session: Session) -> list[TimeCoefficient]:
    return list(
        session.scalars(
            select(TimeCoefficient).order_by(
                TimeCoefficient.subject_id,
                TimeCoefficient.task_type,
                TimeCoefficient.difficulty,
            )
        ).all()
    )


def list_time_adjustments(session: Session) -> list[TimeAdjustment]:
    return list(
        session.scalars(
            select(TimeAdjustment).order_by(TimeAdjustment.occurred_at, TimeAdjustment.created_at)
        ).all()
    )


def _get_task(session: Session, task_id: str) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise TimeCalibrationError(
            "task for time calibration not found",
            code="TIME_CALIBRATION_TASK_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"task_id": task_id},
        )
    return task


def _get_or_create_coefficient(
    session: Session,
    *,
    subject_id: str,
    task_type: str,
    difficulty: str,
) -> TimeCoefficient:
    coefficient = get_time_coefficient(
        session,
        subject_id=subject_id,
        task_type=task_type,
        difficulty=difficulty,
    )
    if coefficient is not None:
        return coefficient
    coefficient = TimeCoefficient(
        id=str(uuid4()),
        subject_id=subject_id,
        task_type=task_type,
        difficulty=difficulty,
        coefficient=DEFAULT_COEFFICIENT,
        sample_count=0,
        overtime_streak=0,
        rule_version=TIME_CALIBRATION_RULE_VERSION,
        rationale_json={"source": "default"},
    )
    session.add(coefficient)
    session.flush()
    return coefficient


def _ratio_for_update(
    *,
    estimated_minutes: int,
    actual_minutes: int,
) -> tuple[float | None, float | None, str | None]:
    if estimated_minutes <= 0 or actual_minutes <= 0:
        return None, None, "ZERO_DURATION"
    raw_ratio = actual_minutes / estimated_minutes
    if raw_ratio < MIN_ACCEPTED_RATIO or raw_ratio > MAX_ACCEPTED_RATIO:
        return raw_ratio, None, "EXTREME_RATIO"
    applied_ratio = min(max(raw_ratio, MIN_APPLIED_RATIO), MAX_APPLIED_RATIO)
    return raw_ratio, applied_ratio, None


def _clamp_coefficient(value: float) -> float:
    return round(min(max(value, MIN_COEFFICIENT), MAX_COEFFICIENT), 4)


def _scope_subject_id(subject_id: str | None) -> str:
    return subject_id or DEFAULT_SUBJECT_ID


def _scope_difficulty(difficulty: str | None) -> str:
    return difficulty or DEFAULT_DIFFICULTY
