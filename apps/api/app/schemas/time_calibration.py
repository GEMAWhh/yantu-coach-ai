from datetime import datetime
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

from app.models.time_calibration import TimeAdjustment, TimeCoefficient


class TimeCoefficientResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    subject_id: str
    task_type: str
    difficulty: str
    coefficient: float
    sample_count: int
    overtime_streak: int
    last_ratio: float | None
    last_estimated_minutes: int | None
    last_actual_minutes: int | None
    last_task_result_id: str | None
    rule_version: Literal["time-calibration-v1.0.0"]
    rationale: dict[str, object]

    @classmethod
    def from_model(cls, coefficient: TimeCoefficient) -> "TimeCoefficientResponse":
        return cls(
            id=coefficient.id,
            subject_id=coefficient.subject_id,
            task_type=coefficient.task_type,
            difficulty=coefficient.difficulty,
            coefficient=coefficient.coefficient,
            sample_count=coefficient.sample_count,
            overtime_streak=coefficient.overtime_streak,
            last_ratio=coefficient.last_ratio,
            last_estimated_minutes=coefficient.last_estimated_minutes,
            last_actual_minutes=coefficient.last_actual_minutes,
            last_task_result_id=coefficient.last_task_result_id,
            rule_version=cast(Literal["time-calibration-v1.0.0"], coefficient.rule_version),
            rationale=coefficient.rationale_json,
        )


class TimeCoefficientListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[TimeCoefficientResponse]
    total: int


class TimeAdjustmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    coefficient_id: str
    task_id: str
    task_result_id: str
    subject_id: str
    task_type: str
    difficulty: str
    estimated_minutes: int
    actual_minutes: int
    raw_ratio: float | None
    applied_ratio: float | None
    previous_coefficient: float
    new_coefficient: float
    ignored: bool
    ignore_reason: str | None
    overtime: bool
    suggested_split: bool
    rule_version: Literal["time-calibration-v1.0.0"]
    occurred_at: datetime

    @classmethod
    def from_model(cls, adjustment: TimeAdjustment) -> "TimeAdjustmentResponse":
        return cls(
            id=adjustment.id,
            coefficient_id=adjustment.coefficient_id,
            task_id=adjustment.task_id,
            task_result_id=adjustment.task_result_id,
            subject_id=adjustment.subject_id,
            task_type=adjustment.task_type,
            difficulty=adjustment.difficulty,
            estimated_minutes=adjustment.estimated_minutes,
            actual_minutes=adjustment.actual_minutes,
            raw_ratio=adjustment.raw_ratio,
            applied_ratio=adjustment.applied_ratio,
            previous_coefficient=adjustment.previous_coefficient,
            new_coefficient=adjustment.new_coefficient,
            ignored=adjustment.ignored,
            ignore_reason=adjustment.ignore_reason,
            overtime=adjustment.overtime,
            suggested_split=adjustment.suggested_split,
            rule_version=cast(Literal["time-calibration-v1.0.0"], adjustment.rule_version),
            occurred_at=adjustment.occurred_at,
        )


class TimeAdjustmentListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[TimeAdjustmentResponse]
    total: int
