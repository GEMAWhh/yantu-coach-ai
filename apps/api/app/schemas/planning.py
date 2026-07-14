from __future__ import annotations

from datetime import date, datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.models.planning import Goal, Task, TaskResult
from app.planning.engine import PlanningCandidate, TodayPlan
from app.planning.service import GoalTreeNode

GoalLevel = Literal["semester", "quarter", "month", "week", "day"]
GoalStatus = Literal["draft", "active", "completed", "delayed", "archived", "cancelled"]
TaskStatus = Literal["pending", "in_progress", "completed", "skipped", "withdrawn"]
TaskResultType = Literal["completed", "partial", "wrong", "unknown"]
EnergyLevel = Literal["low", "medium", "high"]
CognitiveLoad = Literal["low", "medium", "high"]


class GoalCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: GoalLevel
    title: str = Field(min_length=1, max_length=240)
    parent_id: str | None = None
    subject_id: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_minutes: int = Field(default=0, ge=0)
    completion_standard: str | None = None
    risk_status: str = Field(default="normal", min_length=1, max_length=40)
    status: GoalStatus = "active"
    adjustment_reason: str | None = None


class GoalUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    completion_standard: str | None = None
    risk_status: str | None = Field(default=None, min_length=1, max_length=40)
    status: GoalStatus | None = None
    adjustment_reason: str | None = None


class GoalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    is_deleted: bool
    deleted_at: datetime | None
    parent_id: str | None
    level: GoalLevel
    subject_id: str | None
    title: str
    description: str | None
    start_date: date | None
    end_date: date | None
    estimated_minutes: int
    actual_minutes: int
    completion_standard: str | None
    progress: int
    risk_status: str
    status: GoalStatus
    adjustment_reason: str | None

    @classmethod
    def from_model(cls, goal: Goal) -> GoalResponse:
        return cls(
            id=goal.id,
            version=goal.version,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
            created_by=goal.created_by,
            is_deleted=goal.is_deleted,
            deleted_at=goal.deleted_at,
            parent_id=goal.parent_id,
            level=cast(GoalLevel, goal.level),
            subject_id=goal.subject_id,
            title=goal.title,
            description=goal.description,
            start_date=goal.start_date,
            end_date=goal.end_date,
            estimated_minutes=goal.estimated_minutes,
            actual_minutes=goal.actual_minutes,
            completion_standard=goal.completion_standard,
            progress=goal.progress,
            risk_status=goal.risk_status,
            status=cast(GoalStatus, goal.status),
            adjustment_reason=goal.adjustment_reason,
        )


class GoalTreeResponse(GoalResponse):
    children: list[GoalTreeResponse] = Field(default_factory=list)

    @classmethod
    def from_tree(cls, tree: GoalTreeNode) -> GoalTreeResponse:
        goal = tree.goal
        return cls(
            id=goal.id,
            version=goal.version,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
            created_by=goal.created_by,
            is_deleted=goal.is_deleted,
            deleted_at=goal.deleted_at,
            parent_id=goal.parent_id,
            level=cast(GoalLevel, goal.level),
            subject_id=goal.subject_id,
            title=goal.title,
            description=goal.description,
            start_date=goal.start_date,
            end_date=goal.end_date,
            estimated_minutes=goal.estimated_minutes,
            actual_minutes=goal.actual_minutes,
            completion_standard=goal.completion_standard,
            progress=goal.progress,
            risk_status=goal.risk_status,
            status=cast(GoalStatus, goal.status),
            adjustment_reason=goal.adjustment_reason,
            children=[cls.from_tree(child) for child in tree.children],
        )


class GoalTreeListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[GoalTreeResponse]
    total: int


class TaskCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=240)
    planned_date: date
    estimated_minutes: int = Field(ge=0)
    source_type: str = Field(min_length=1, max_length=80)
    goal_id: str | None = None
    subject_id: str | None = None
    knowledge_node_id: str | None = None
    wrong_record_id: str | None = None
    review_schedule_id: str | None = None
    task_type: str = Field(default="study", min_length=1, max_length=60)
    priority: str = Field(default="normal", min_length=1, max_length=40)
    source_id: str | None = None
    difficulty: str | None = None
    cognitive_load: str | None = None
    current_stage: int | None = Field(default=None, ge=0, le=8)
    target_stage: int | None = Field(default=None, ge=0, le=8)
    reason: str | None = None
    completion_standard: str | None = None
    prerequisite_status: str = Field(default="unknown", min_length=1, max_length=40)
    status: TaskStatus = "pending"


class TaskUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str | None = Field(default=None, min_length=1, max_length=240)
    planned_date: date | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    priority: str | None = Field(default=None, min_length=1, max_length=40)
    reason: str | None = None
    completion_standard: str | None = None
    prerequisite_status: str | None = Field(default=None, min_length=1, max_length=40)
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    is_deleted: bool
    deleted_at: datetime | None
    goal_id: str | None
    subject_id: str | None
    knowledge_node_id: str | None
    title: str
    task_type: str
    priority: str
    source_type: str
    source_id: str | None
    planned_date: date
    estimated_minutes: int
    difficulty: str | None
    cognitive_load: str | None
    current_stage: int | None
    target_stage: int | None
    reason: str | None
    completion_standard: str | None
    prerequisite_status: str
    status: TaskStatus

    @classmethod
    def from_model(cls, task: Task) -> TaskResponse:
        return cls(
            id=task.id,
            version=task.version,
            created_at=task.created_at,
            updated_at=task.updated_at,
            created_by=task.created_by,
            is_deleted=task.is_deleted,
            deleted_at=task.deleted_at,
            goal_id=task.goal_id,
            subject_id=task.subject_id,
            knowledge_node_id=task.knowledge_node_id,
            title=task.title,
            task_type=task.task_type,
            priority=task.priority,
            source_type=task.source_type,
            source_id=task.source_id,
            planned_date=task.planned_date,
            estimated_minutes=task.estimated_minutes,
            difficulty=task.difficulty,
            cognitive_load=task.cognitive_load,
            current_stage=task.current_stage,
            target_stage=task.target_stage,
            reason=task.reason,
            completion_standard=task.completion_standard,
            prerequisite_status=task.prerequisite_status,
            status=cast(TaskStatus, task.status),
        )


class TaskListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[TaskResponse]
    total: int


class TodayResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    tasks: list[TaskResponse]
    total_tasks: int
    estimated_minutes: int


class PlanningCandidateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    subject_id: str = Field(min_length=1)
    estimated_minutes: int = Field(ge=0)
    cognitive_load: CognitiveLoad
    prerequisite_status: str = "satisfied"
    source_type: str = "manual"
    source_id: str | None = None
    task_type: str = "study"
    fixed: bool = False
    failure_streak: int = Field(default=0, ge=0)
    overtime_count: int = Field(default=0, ge=0)
    deadline_urgency: int = Field(default=0, ge=0, le=100)
    review_due: int = Field(default=0, ge=0, le=100)
    knowledge_importance: int = Field(default=0, ge=0, le=100)
    weakness: int = Field(default=0, ge=0, le=100)
    parent_goal_risk: int = Field(default=0, ge=0, le=100)
    repeat_error: int = Field(default=0, ge=0, le=100)
    energy_fit: int = Field(default=50, ge=0, le=100)

    def to_candidate(self) -> PlanningCandidate:
        return PlanningCandidate(**self.model_dump())


class TodayGenerateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    available_minutes: int = Field(ge=0)
    energy: EnergyLevel
    subject_filter: str | None = None
    candidates: list[PlanningCandidateInput]


class CandidateScoreResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: float
    breakdown: dict[str, float]


class GeneratedTaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    subject_id: str
    source_type: str
    source_id: str | None
    scheduled_minutes: int
    score: CandidateScoreResponse
    explanations: list[str]


class RejectedTaskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    subject_id: str
    score: CandidateScoreResponse
    reasons: list[str]


class TodayGenerateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_version: Literal["planning-v1.0.0"]
    available_minutes: int
    schedulable_minutes: int
    planned_minutes: int
    buffer_minutes: int
    selected: list[GeneratedTaskResponse]
    rejected: list[RejectedTaskResponse]

    @classmethod
    def from_plan(cls, plan: TodayPlan) -> TodayGenerateResponse:
        return cls(
            rule_version="planning-v1.0.0",
            available_minutes=plan.available_minutes,
            schedulable_minutes=plan.schedulable_minutes,
            planned_minutes=plan.planned_minutes,
            buffer_minutes=plan.buffer_minutes,
            selected=[
                GeneratedTaskResponse(
                    id=item.candidate.id,
                    title=item.candidate.title,
                    subject_id=item.candidate.subject_id,
                    source_type=item.candidate.source_type,
                    source_id=item.candidate.source_id,
                    scheduled_minutes=item.scheduled_minutes,
                    score=CandidateScoreResponse(
                        total=item.score.total,
                        breakdown=item.score.breakdown,
                    ),
                    explanations=item.explanations,
                )
                for item in plan.selected
            ],
            rejected=[
                RejectedTaskResponse(
                    id=item.candidate.id,
                    title=item.candidate.title,
                    subject_id=item.candidate.subject_id,
                    score=CandidateScoreResponse(
                        total=item.score.total,
                        breakdown=item.score.breakdown,
                    ),
                    reasons=item.reasons,
                )
                for item in plan.rejected
            ],
        )


class TaskResultCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_type: TaskResultType
    completion_ratio: int = Field(ge=0, le=100)
    actual_minutes: int = Field(ge=0)
    question_count: int | None = Field(default=None, ge=0)
    correct_count: int | None = Field(default=None, ge=0)
    accuracy: int | None = Field(default=None, ge=0, le=100)
    confidence: int | None = Field(default=None, ge=0, le=100)
    hint_level: int | None = Field(default=None, ge=0)
    focus_level: int | None = Field(default=None, ge=0, le=100)
    difficulty_rating: int | None = Field(default=None, ge=0, le=100)
    problem_description: str | None = None
    confirmed_at: datetime | None = None


class TaskResultResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    task_id: str
    result_type: TaskResultType
    completion_ratio: int
    actual_minutes: int
    question_count: int | None
    correct_count: int | None
    accuracy: int | None
    confidence: int | None
    hint_level: int | None
    focus_level: int | None
    difficulty_rating: int | None
    problem_description: str | None
    confirmed_at: datetime

    @classmethod
    def from_model(cls, result: TaskResult) -> TaskResultResponse:
        return cls(
            id=result.id,
            version=result.version,
            created_at=result.created_at,
            updated_at=result.updated_at,
            task_id=result.task_id,
            result_type=cast(TaskResultType, result.result_type),
            completion_ratio=result.completion_ratio,
            actual_minutes=result.actual_minutes,
            question_count=result.question_count,
            correct_count=result.correct_count,
            accuracy=result.accuracy,
            confidence=result.confidence,
            hint_level=result.hint_level,
            focus_level=result.focus_level,
            difficulty_rating=result.difficulty_rating,
            problem_description=result.problem_description,
            confirmed_at=result.confirmed_at,
        )


class TaskResultSubmitResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: TaskResultResponse
    created: bool
