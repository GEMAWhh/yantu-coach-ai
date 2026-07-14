from datetime import date, datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import ReviewResult, ReviewSchedule
from app.planning.engine import PlanningCandidate
from app.reviews.service import (
    REVIEW_RULE_VERSION,
    ReviewDueItem,
    ReviewResultType,
    ReviewSubmission,
)


class ReviewScheduleResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    knowledge_node_id: str
    subject_id: str | None
    current_stage: int
    status: Literal["active", "paused", "completed", "archived"]
    due_at: datetime
    interval_days: int
    pass_streak: int
    fail_streak: int
    last_reviewed_at: datetime | None
    last_result_id: str | None
    source_snapshot_id: str | None
    rule_version: Literal["review-v1.0.0"]
    next_reason: str

    @classmethod
    def from_model(cls, schedule: ReviewSchedule) -> "ReviewScheduleResponse":
        return cls(
            id=schedule.id,
            version=schedule.version,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
            knowledge_node_id=schedule.knowledge_node_id,
            subject_id=schedule.subject_id,
            current_stage=schedule.current_stage,
            status=cast(Literal["active", "paused", "completed", "archived"], schedule.status),
            due_at=schedule.due_at,
            interval_days=schedule.interval_days,
            pass_streak=schedule.pass_streak,
            fail_streak=schedule.fail_streak,
            last_reviewed_at=schedule.last_reviewed_at,
            last_result_id=schedule.last_result_id,
            source_snapshot_id=schedule.source_snapshot_id,
            rule_version="review-v1.0.0",
            next_reason=schedule.next_reason,
        )


class ReviewCandidateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    subject_id: str
    estimated_minutes: int
    cognitive_load: Literal["low", "medium", "high"]
    source_type: str
    source_id: str | None
    task_type: str
    review_due: int
    knowledge_importance: int

    @classmethod
    def from_candidate(cls, candidate: PlanningCandidate) -> "ReviewCandidateResponse":
        return cls(
            id=candidate.id,
            title=candidate.title,
            subject_id=candidate.subject_id,
            estimated_minutes=candidate.estimated_minutes,
            cognitive_load=candidate.cognitive_load,
            source_type=candidate.source_type,
            source_id=candidate.source_id,
            task_type=candidate.task_type,
            review_due=candidate.review_due,
            knowledge_importance=candidate.knowledge_importance,
        )


class DueReviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schedule: ReviewScheduleResponse
    knowledge_node_name: str
    candidate: ReviewCandidateResponse

    @classmethod
    def from_due_item(cls, item: ReviewDueItem) -> "DueReviewResponse":
        return cls(
            schedule=ReviewScheduleResponse.from_model(item.schedule),
            knowledge_node_name=item.knowledge_node.name,
            candidate=ReviewCandidateResponse.from_candidate(item.candidate),
        )


class DueReviewListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    items: list[DueReviewResponse]
    total: int


class ReviewRecalculateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[ReviewScheduleResponse]
    total: int


class ReviewResultCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_type: ReviewResultType
    score: int | None = Field(default=None, ge=0, le=100)
    sample_count: int = Field(default=0, ge=0)
    correct_count: int | None = Field(default=None, ge=0)
    accuracy: int | None = Field(default=None, ge=0, le=100)
    occurred_at: datetime | None = None


class ReviewResultResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    schedule_id: str
    knowledge_node_id: str
    result_type: ReviewResultType
    score: int | None
    sample_count: int
    correct_count: int | None
    accuracy: int | None
    occurred_at: datetime
    independent_timepoint: bool
    evidence_id: str | None
    snapshot_id: str | None

    @classmethod
    def from_model(cls, result: ReviewResult) -> "ReviewResultResponse":
        return cls(
            id=result.id,
            version=result.version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            schedule_id=result.schedule_id,
            knowledge_node_id=result.knowledge_node_id,
            result_type=cast(ReviewResultType, result.result_type),
            score=result.score,
            sample_count=result.sample_count,
            correct_count=result.correct_count,
            accuracy=result.accuracy,
            occurred_at=result.occurred_at,
            independent_timepoint=result.independent_timepoint,
            evidence_id=result.evidence_id,
            snapshot_id=result.snapshot_id,
        )


class ReviewResultSubmitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: ReviewResultResponse
    schedule: ReviewScheduleResponse
    created: bool
    evaluation_new_stage: int | None
    evaluation_reason: str | None
    rule_version: Literal["review-v1.0.0"]

    @classmethod
    def from_submission(cls, submission: ReviewSubmission) -> "ReviewResultSubmitResponse":
        return cls(
            result=ReviewResultResponse.from_model(submission.result),
            schedule=ReviewScheduleResponse.from_model(submission.schedule),
            created=submission.created,
            evaluation_new_stage=(
                submission.evaluation.new_stage if submission.evaluation is not None else None
            ),
            evaluation_reason=(
                submission.evaluation.transition_reason
                if submission.evaluation is not None
                else None
            ),
            rule_version=cast(Literal["review-v1.0.0"], REVIEW_RULE_VERSION),
        )
