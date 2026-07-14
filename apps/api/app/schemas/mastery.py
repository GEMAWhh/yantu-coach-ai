from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.mastery.service import EvidenceType, MasteryEvaluation
from app.models.mastery import MasteryEvidence, MasterySnapshot


class MasteryEvidenceCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType
    source_type: str = Field(min_length=1, max_length=80)
    source_id: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    sample_count: int = Field(default=0, ge=0)
    correct_count: int | None = Field(default=None, ge=0)
    accuracy: int | None = Field(default=None, ge=0, le=100)
    hint_level: int | None = Field(default=None, ge=0)
    is_original: bool = False
    occurred_at: datetime | None = None
    confirmed: bool = True
    metadata_json: dict[str, Any] | None = None


class MasteryEvidenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    created_at: datetime
    updated_at: datetime
    knowledge_node_id: str
    evidence_type: EvidenceType
    source_type: str
    source_id: str | None
    score: int | None
    sample_count: int
    correct_count: int | None
    accuracy: int | None
    hint_level: int | None
    is_original: bool
    occurred_at: datetime
    confirmed: bool
    metadata_json: dict[str, Any] | None

    @classmethod
    def from_model(cls, evidence: MasteryEvidence) -> "MasteryEvidenceResponse":
        return cls(
            id=evidence.id,
            version=evidence.version,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
            knowledge_node_id=evidence.knowledge_node_id,
            evidence_type=cast(EvidenceType, evidence.evidence_type),
            source_type=evidence.source_type,
            source_id=evidence.source_id,
            score=evidence.score,
            sample_count=evidence.sample_count,
            correct_count=evidence.correct_count,
            accuracy=evidence.accuracy,
            hint_level=evidence.hint_level,
            is_original=evidence.is_original,
            occurred_at=evidence.occurred_at,
            confirmed=evidence.confirmed,
            metadata_json=evidence.metadata_json,
        )


class MasteryEvidenceListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasteryEvidenceResponse]
    total: int


class MasteryEvaluateRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_stage: int | None = Field(default=None, ge=0, le=8)


class MasteryRollbackRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_stage: int = Field(ge=0, le=8)
    evidence_id: str
    reason: str = Field(min_length=1, max_length=200)


class MasterySnapshotResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    knowledge_node_id: str
    previous_stage: int
    stage: int
    evaluated_at: datetime
    rule_version: str
    transition_reason: str
    evidence_ids: list[str]
    computed_metrics: dict[str, Any]
    blocking_reasons: list[str]
    remediation: dict[str, Any] | None

    @classmethod
    def from_model(cls, snapshot: MasterySnapshot) -> "MasterySnapshotResponse":
        return cls(
            id=snapshot.id,
            knowledge_node_id=snapshot.knowledge_node_id,
            previous_stage=snapshot.previous_stage,
            stage=snapshot.stage,
            evaluated_at=snapshot.evaluated_at,
            rule_version=snapshot.rule_version,
            transition_reason=snapshot.transition_reason,
            evidence_ids=snapshot.evidence_ids_json,
            computed_metrics=snapshot.computed_metrics_json,
            blocking_reasons=snapshot.blocking_reasons_json,
            remediation=snapshot.remediation_json,
        )


class MasteryHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[MasterySnapshotResponse]
    total: int


class MasteryEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    knowledge_node_id: str
    previous_stage: int
    new_stage: int
    changed: bool
    rule_version: Literal["mastery-v1.0.0"]
    evidence_ids: list[str]
    blocking_reasons: list[str]
    transition_reason: str
    next_action: str
    snapshot_id: str | None
    remediation: dict[str, Any] | None

    @classmethod
    def from_evaluation(cls, evaluation: MasteryEvaluation) -> "MasteryEvaluationResponse":
        return cls(
            knowledge_node_id=evaluation.knowledge_node_id,
            previous_stage=evaluation.previous_stage,
            new_stage=evaluation.new_stage,
            changed=evaluation.changed,
            rule_version="mastery-v1.0.0",
            evidence_ids=evaluation.evidence_ids,
            blocking_reasons=evaluation.blocking_reasons,
            transition_reason=evaluation.transition_reason,
            next_action=evaluation.next_action,
            snapshot_id=evaluation.snapshot.id if evaluation.snapshot is not None else None,
            remediation=evaluation.remediation,
        )
