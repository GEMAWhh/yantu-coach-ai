from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class CountBucket(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    count: int


class GraphNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    object_type: Literal["knowledge_node"]
    object_id: str
    label: str
    subject_id: str | None
    status: str
    metrics: dict[str, Any]


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    source_id: str
    target_id: str
    relation_type: str
    weight: int
    confirmed: bool


class GraphResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    total_nodes: int
    total_edges: int


class WeakNodeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_type: Literal["knowledge_node"]
    object_id: str
    label: str
    subject_id: str | None
    latest_stage: int
    evidence_count: int
    repeat_error_rate: int | None
    blocking_reasons: list[str]


class WeakGraphResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[WeakNodeResponse]
    total: int


class AnalyticsOverviewResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    knowledge_nodes: int
    goals: int
    tasks: int
    task_results: int
    wrong_records: int
    mastery_snapshots: int
    average_goal_progress: int
    task_status: list[CountBucket]
    goal_risk: list[CountBucket]


class TimeBySubjectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: str
    estimated_minutes: int
    actual_minutes: int


class AnalyticsTimeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    estimated_minutes: int
    actual_minutes: int
    by_subject: list[TimeBySubjectResponse]


class ErrorByKnowledgeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    knowledge_node_id: str
    count: int


class AnalyticsErrorsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_wrong_records: int
    by_status: list[CountBucket]
    by_knowledge_node: list[ErrorByKnowledgeResponse]


class AnalyticsMasteryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    latest_snapshot_count: int
    weak_node_count: int
    stage_distribution: list[CountBucket]


class GoalRiskItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_type: Literal["goal"]
    object_id: str
    title: str
    level: str
    risk_status: str
    status: str
    progress: int


class AnalyticsGoalRiskResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_goals: int
    by_risk_status: list[CountBucket]
    risky_goals: list[GoalRiskItemResponse]
