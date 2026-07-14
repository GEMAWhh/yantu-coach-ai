from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.knowledge.service import get_knowledge_node
from app.mastery.service import (
    STAGE_LABELS,
    MasteryEvaluation,
    create_mastery_evidence,
    evaluate_mastery,
    rollback_mastery,
)
from app.models.base import utc_now
from app.models.knowledge import KnowledgeNode
from app.models.mastery import MasterySnapshot
from app.models.review import ReviewResult, ReviewSchedule
from app.planning.engine import PlanningCandidate

REVIEW_RULE_VERSION = "review-v1.0.0"
PASSING_REVIEW_SCORE = 70
MAX_REVIEW_INTERVAL_DAYS = 90
DEFAULT_REVIEW_MINUTES = 20

ReviewResultType = Literal["pass", "fail"]

BASE_INTERVAL_DAYS = {
    1: 1,
    2: 1,
    3: 3,
    4: 7,
    5: 14,
    6: 21,
    7: 30,
    8: 1,
}


class ReviewError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "REVIEW_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class ReviewSubmission:
    result: ReviewResult
    schedule: ReviewSchedule
    created: bool
    evaluation: MasteryEvaluation | None


@dataclass(frozen=True)
class ReviewDueItem:
    schedule: ReviewSchedule
    knowledge_node: KnowledgeNode
    candidate: PlanningCandidate


def ensure_review_schedule(
    session: Session,
    *,
    knowledge_node_id: str,
    stage: int | None = None,
    reviewed_at: datetime | None = None,
    source_snapshot_id: str | None = None,
) -> ReviewSchedule:
    node = get_knowledge_node(session, knowledge_node_id)
    snapshot = _latest_snapshot(session, knowledge_node_id)
    resolved_stage = stage if stage is not None else (snapshot.stage if snapshot is not None else 1)
    _validate_stage_for_review(resolved_stage)
    base_interval = _base_interval_days(resolved_stage)
    schedule = _latest_active_schedule(session, knowledge_node_id)
    anchor = reviewed_at or utc_now()
    due_at = anchor + timedelta(days=base_interval)
    if schedule is None:
        schedule = ReviewSchedule(
            id=str(uuid4()),
            knowledge_node_id=node.id,
            subject_id=node.subject_id,
            current_stage=resolved_stage,
            due_at=due_at,
            interval_days=base_interval,
            source_snapshot_id=source_snapshot_id or (snapshot.id if snapshot else None),
            rule_version=REVIEW_RULE_VERSION,
            next_reason=f"base_interval:{_stage_key(resolved_stage)}",
        )
        session.add(schedule)
    else:
        schedule.subject_id = node.subject_id
        schedule.current_stage = resolved_stage
        schedule.due_at = due_at
        schedule.interval_days = base_interval
        schedule.source_snapshot_id = source_snapshot_id or (snapshot.id if snapshot else None)
        schedule.rule_version = REVIEW_RULE_VERSION
        schedule.next_reason = f"base_interval:{_stage_key(resolved_stage)}"
    session.flush()
    return schedule


def recalculate_review_schedules(session: Session) -> list[ReviewSchedule]:
    latest = _latest_snapshots(session)
    schedules = []
    for snapshot in latest:
        if snapshot.stage <= 0:
            continue
        schedules.append(
            ensure_review_schedule(
                session,
                knowledge_node_id=snapshot.knowledge_node_id,
                stage=snapshot.stage,
                reviewed_at=snapshot.evaluated_at,
                source_snapshot_id=snapshot.id,
            )
        )
    return schedules


def list_due_reviews(session: Session, *, due_on: date) -> list[ReviewDueItem]:
    due_before = datetime.combine(due_on, time.max, tzinfo=UTC)
    schedules = session.scalars(
        select(ReviewSchedule)
        .where(
            ReviewSchedule.status == "active",
            ReviewSchedule.is_deleted.is_(False),
            ReviewSchedule.due_at <= due_before,
        )
        .order_by(ReviewSchedule.due_at, ReviewSchedule.knowledge_node_id)
    ).all()
    items = []
    for schedule in schedules:
        node = get_knowledge_node(session, schedule.knowledge_node_id)
        items.append(
            ReviewDueItem(
                schedule=schedule,
                knowledge_node=node,
                candidate=_candidate_for_schedule(schedule, node),
            )
        )
    return items


def due_reviews_as_planning_candidates(
    session: Session,
    *,
    due_on: date,
) -> list[PlanningCandidate]:
    return [item.candidate for item in list_due_reviews(session, due_on=due_on)]


def submit_review_result(
    session: Session,
    schedule_id: str,
    *,
    result_type: ReviewResultType,
    score: int | None = None,
    sample_count: int = 0,
    correct_count: int | None = None,
    accuracy: int | None = None,
    occurred_at: datetime | None = None,
    idempotency_key: str | None = None,
    request_id: str | None = None,
) -> ReviewSubmission:
    _validate_result(result_type, score=score, accuracy=accuracy, sample_count=sample_count)
    schedule = get_review_schedule(session, schedule_id)
    existing = _idempotent_result(session, schedule_id, idempotency_key)
    if existing is not None:
        return ReviewSubmission(
            result=existing,
            schedule=schedule,
            created=False,
            evaluation=None,
        )

    occurred = occurred_at or utc_now()
    independent = _is_independent_timepoint(schedule, occurred)
    result = ReviewResult(
        id=str(uuid4()),
        schedule_id=schedule.id,
        knowledge_node_id=schedule.knowledge_node_id,
        idempotency_key=idempotency_key,
        result_type=result_type,
        score=score,
        sample_count=sample_count,
        correct_count=correct_count,
        accuracy=accuracy,
        occurred_at=occurred,
        independent_timepoint=independent,
        request_id=request_id,
    )
    session.add(result)
    session.flush()

    evaluation: MasteryEvaluation | None = None
    if independent:
        evaluation = _apply_independent_review_result(session, schedule, result)
    else:
        schedule.next_reason = "same_day_redo_not_independent"
        schedule.last_result_id = result.id

    result.snapshot_id = (
        evaluation.snapshot.id if evaluation is not None and evaluation.snapshot else None
    )
    schedule.last_result_id = result.id
    session.flush()
    return ReviewSubmission(result=result, schedule=schedule, created=True, evaluation=evaluation)


def get_review_schedule(session: Session, schedule_id: str) -> ReviewSchedule:
    schedule = session.get(ReviewSchedule, schedule_id)
    if schedule is None or schedule.is_deleted:
        raise ReviewError(
            "review schedule not found",
            code="REVIEW_SCHEDULE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"schedule_id": schedule_id},
        )
    return schedule


def _apply_independent_review_result(
    session: Session,
    schedule: ReviewSchedule,
    result: ReviewResult,
) -> MasteryEvaluation:
    evidence = create_mastery_evidence(
        session,
        knowledge_node_id=schedule.knowledge_node_id,
        evidence_type="interval_test",
        source_type="review_schedule",
        source_id=schedule.id,
        score=result.score,
        sample_count=result.sample_count,
        correct_count=result.correct_count,
        accuracy=result.accuracy,
        occurred_at=result.occurred_at,
        metadata_json={"review_result_id": result.id},
    )
    result.evidence_id = evidence.id

    if _review_passed(result):
        evaluation = evaluate_mastery(session, schedule.knowledge_node_id)
        schedule.pass_streak += 1
        schedule.fail_streak = 0
        interval_days = _extended_interval_days(schedule.current_stage, schedule.pass_streak)
        schedule.interval_days = interval_days
        schedule.due_at = result.occurred_at + timedelta(days=interval_days)
        schedule.last_reviewed_at = result.occurred_at
        schedule.next_reason = f"passed_independent_review:{schedule.pass_streak}"
        return evaluation

    evaluation = evaluate_mastery(session, schedule.knowledge_node_id)
    if not evaluation.changed and schedule.current_stage > 1:
        evaluation = rollback_mastery(
            session,
            schedule.knowledge_node_id,
            target_stage=schedule.current_stage - 1,
            evidence_id=evidence.id,
            reason="review_failed_regression",
        )
    schedule.current_stage = evaluation.new_stage
    schedule.pass_streak = 0
    schedule.fail_streak += 1
    interval_days = _shortened_interval_days(schedule.current_stage)
    schedule.interval_days = interval_days
    schedule.due_at = result.occurred_at + timedelta(days=interval_days)
    schedule.last_reviewed_at = result.occurred_at
    schedule.next_reason = "failed_review_short_interval"
    return evaluation


def _candidate_for_schedule(schedule: ReviewSchedule, node: KnowledgeNode) -> PlanningCandidate:
    return PlanningCandidate(
        id=f"review:{schedule.id}",
        title=f"复习：{node.name}",
        subject_id=node.subject_id or schedule.subject_id or "unknown",
        estimated_minutes=DEFAULT_REVIEW_MINUTES,
        cognitive_load="medium",
        prerequisite_status="satisfied",
        source_type="review_schedule",
        source_id=schedule.id,
        task_type="review",
        deadline_urgency=80,
        review_due=100,
        knowledge_importance=node.importance or 50,
        weakness=50 if schedule.fail_streak else 20,
        parent_goal_risk=20,
        repeat_error=20 if schedule.fail_streak else 0,
    )


def _idempotent_result(
    session: Session,
    schedule_id: str,
    idempotency_key: str | None,
) -> ReviewResult | None:
    if idempotency_key is None:
        return None
    return session.scalar(
        select(ReviewResult).where(
            ReviewResult.schedule_id == schedule_id,
            ReviewResult.idempotency_key == idempotency_key,
        )
    )


def _latest_active_schedule(session: Session, knowledge_node_id: str) -> ReviewSchedule | None:
    return session.scalar(
        select(ReviewSchedule)
        .where(
            ReviewSchedule.knowledge_node_id == knowledge_node_id,
            ReviewSchedule.status == "active",
            ReviewSchedule.is_deleted.is_(False),
        )
        .order_by(literal_column("rowid").desc())
    )


def _latest_snapshot(session: Session, knowledge_node_id: str) -> MasterySnapshot | None:
    return session.scalar(
        select(MasterySnapshot)
        .where(MasterySnapshot.knowledge_node_id == knowledge_node_id)
        .order_by(literal_column("rowid").desc())
    )


def _latest_snapshots(session: Session) -> list[MasterySnapshot]:
    snapshots = session.scalars(
        select(MasterySnapshot).order_by(MasterySnapshot.knowledge_node_id, literal_column("rowid"))
    ).all()
    latest: dict[str, MasterySnapshot] = {}
    for snapshot in snapshots:
        latest[snapshot.knowledge_node_id] = snapshot
    return list(latest.values())


def _validate_stage_for_review(stage: int) -> None:
    if stage <= 0 or stage not in STAGE_LABELS:
        raise ReviewError(
            "review schedule requires a learned mastery stage",
            code="REVIEW_STAGE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"stage": stage},
        )


def _validate_result(
    result_type: str,
    *,
    score: int | None,
    accuracy: int | None,
    sample_count: int,
) -> None:
    if result_type not in {"pass", "fail"}:
        raise ReviewError(
            "unsupported review result type",
            code="REVIEW_RESULT_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"result_type": result_type},
        )
    if sample_count < 0:
        raise ReviewError("review sample_count must not be negative", code="REVIEW_COUNT_INVALID")
    for field_name, value in {"score": score, "accuracy": accuracy}.items():
        if value is not None and not 0 <= value <= 100:
            raise ReviewError(
                "review score fields must be 0-100",
                code="REVIEW_SCORE_INVALID",
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                details={"field": field_name, "value": value},
            )


def _is_independent_timepoint(schedule: ReviewSchedule, occurred_at: datetime) -> bool:
    if schedule.last_reviewed_at is None:
        return True
    return schedule.last_reviewed_at.date() != occurred_at.date()


def _review_passed(result: ReviewResult) -> bool:
    score = result.score if result.score is not None else result.accuracy
    if score is None:
        return result.result_type == "pass"
    return result.result_type == "pass" and score >= PASSING_REVIEW_SCORE


def _base_interval_days(stage: int) -> int:
    return BASE_INTERVAL_DAYS.get(stage, 1)


def _extended_interval_days(stage: int, pass_streak: int) -> int:
    return min(_base_interval_days(stage) * (pass_streak + 1), MAX_REVIEW_INTERVAL_DAYS)


def _shortened_interval_days(stage: int) -> int:
    return max(1, _base_interval_days(stage) // 2)


def _stage_key(stage: int) -> str:
    return STAGE_LABELS.get(stage, "unknown")
