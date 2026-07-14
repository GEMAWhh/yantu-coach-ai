from dataclasses import dataclass
from math import floor
from typing import Literal

PLANNING_RULE_VERSION = "planning-v1.0.0"
BUFFER_RATIO_DEFAULT = 0.18
MAX_SINGLE_TASK_MINUTES = 60
MAX_HIGH_COGNITIVE_TASKS_PER_DAY = 2

WEIGHTS = {
    "deadline_urgency": 0.25,
    "review_due": 0.20,
    "knowledge_importance": 0.18,
    "weakness": 0.15,
    "parent_goal_risk": 0.10,
    "repeat_error": 0.07,
    "energy_fit": 0.05,
}

EnergyLevel = Literal["low", "medium", "high"]
CognitiveLoad = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class PlanningCandidate:
    id: str
    title: str
    subject_id: str
    estimated_minutes: int
    cognitive_load: CognitiveLoad
    prerequisite_status: str = "satisfied"
    source_type: str = "manual"
    source_id: str | None = None
    task_type: str = "study"
    fixed: bool = False
    failure_streak: int = 0
    overtime_count: int = 0
    deadline_urgency: int = 0
    review_due: int = 0
    knowledge_importance: int = 0
    weakness: int = 0
    parent_goal_risk: int = 0
    repeat_error: int = 0
    energy_fit: int = 50


@dataclass(frozen=True)
class CandidateScore:
    total: float
    breakdown: dict[str, float]


@dataclass(frozen=True)
class PlannedTask:
    candidate: PlanningCandidate
    score: CandidateScore
    scheduled_minutes: int
    explanations: list[str]


@dataclass(frozen=True)
class RejectedTask:
    candidate: PlanningCandidate
    score: CandidateScore
    reasons: list[str]


@dataclass(frozen=True)
class TodayPlan:
    rule_version: str
    available_minutes: int
    schedulable_minutes: int
    planned_minutes: int
    buffer_minutes: int
    selected: list[PlannedTask]
    rejected: list[RejectedTask]


def generate_today_plan(
    candidates: list[PlanningCandidate],
    *,
    available_minutes: int,
    energy: EnergyLevel,
    subject_filter: str | None = None,
) -> TodayPlan:
    schedulable_minutes = floor(available_minutes * (1 - BUFFER_RATIO_DEFAULT))
    selected: list[PlannedTask] = []
    rejected: list[RejectedTask] = []
    high_cognitive_count = 0
    planned_minutes = 0

    scored = sorted(
        ((_score_candidate(candidate, energy), candidate) for candidate in candidates),
        key=lambda item: (-item[0].total, item[1].id),
    )
    for score, candidate in scored:
        hard_reasons = _hard_rejection_reasons(candidate, energy, subject_filter)
        if hard_reasons:
            rejected.append(RejectedTask(candidate=candidate, score=score, reasons=hard_reasons))
            continue

        scheduled_minutes, scheduling_explanations = _scheduled_minutes(candidate)
        if (
            candidate.cognitive_load == "high"
            and high_cognitive_count >= MAX_HIGH_COGNITIVE_TASKS_PER_DAY
        ):
            rejected.append(
                RejectedTask(
                    candidate=candidate,
                    score=score,
                    reasons=["MAX_HIGH_COGNITIVE_TASKS_REACHED"],
                )
            )
            continue
        if planned_minutes + scheduled_minutes > schedulable_minutes:
            rejected.append(
                RejectedTask(
                    candidate=candidate,
                    score=score,
                    reasons=["INSUFFICIENT_CAPACITY_AFTER_BUFFER"],
                )
            )
            continue

        if candidate.cognitive_load == "high":
            high_cognitive_count += 1
        planned_minutes += scheduled_minutes
        selected.append(
            PlannedTask(
                candidate=candidate,
                score=score,
                scheduled_minutes=scheduled_minutes,
                explanations=[
                    "SELECTED_BY_SCORE",
                    *scheduling_explanations,
                    *[f"SCORE:{key}" for key, value in score.breakdown.items() if value > 0],
                ],
            )
        )

    return TodayPlan(
        rule_version=PLANNING_RULE_VERSION,
        available_minutes=available_minutes,
        schedulable_minutes=schedulable_minutes,
        planned_minutes=planned_minutes,
        buffer_minutes=available_minutes - planned_minutes,
        selected=selected,
        rejected=rejected,
    )


def _hard_rejection_reasons(
    candidate: PlanningCandidate,
    energy: EnergyLevel,
    subject_filter: str | None,
) -> list[str]:
    reasons = []
    if subject_filter is not None and candidate.subject_id != subject_filter:
        reasons.append("SUBJECT_FILTER_MISMATCH")
    if candidate.prerequisite_status in {"blocked", "unmet", "not_satisfied"}:
        reasons.append("PREREQUISITE_NOT_MET")
    if energy == "low" and candidate.cognitive_load == "high":
        reasons.append("LOW_ENERGY_BLOCKS_HIGH_COGNITIVE_LOAD")
    if candidate.failure_streak >= 3:
        reasons.append("REPEATED_NONCOMPLETION_REQUIRES_DIAGNOSIS")
    return reasons


def _scheduled_minutes(candidate: PlanningCandidate) -> tuple[int, list[str]]:
    if (
        candidate.overtime_count >= 2
        and candidate.estimated_minutes > MAX_SINGLE_TASK_MINUTES
        and not candidate.fixed
    ):
        return MAX_SINGLE_TASK_MINUTES, ["TASK_SPLIT_BY_OVERTIME"]
    return candidate.estimated_minutes, []


def _score_candidate(candidate: PlanningCandidate, energy: EnergyLevel) -> CandidateScore:
    raw = {
        "deadline_urgency": candidate.deadline_urgency,
        "review_due": candidate.review_due,
        "knowledge_importance": candidate.knowledge_importance,
        "weakness": candidate.weakness,
        "parent_goal_risk": candidate.parent_goal_risk,
        "repeat_error": candidate.repeat_error,
        "energy_fit": _energy_fit(candidate, energy),
    }
    breakdown = {key: round(raw[key] * weight, 2) for key, weight in WEIGHTS.items()}
    return CandidateScore(total=round(sum(breakdown.values()), 2), breakdown=breakdown)


def _energy_fit(candidate: PlanningCandidate, energy: EnergyLevel) -> int:
    if energy == "low":
        return 100 if candidate.cognitive_load == "low" else 40
    if energy == "high":
        return 100 if candidate.cognitive_load == "high" else 70
    return 80 if candidate.cognitive_load == "medium" else 65
