from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.knowledge.service import get_knowledge_node
from app.models.base import utc_now
from app.models.mastery import MasteryEvidence, MasterySnapshot

MASTERY_RULE_VERSION = "mastery-v1.0.0"

EvidenceType = Literal[
    "reading",
    "self_explanation",
    "closed_book_recall",
    "basic_question",
    "variant_question",
    "integrated_question",
    "interval_test",
    "repeat_deep_cause",
]
EVIDENCE_TYPES = {
    "reading",
    "self_explanation",
    "closed_book_recall",
    "basic_question",
    "variant_question",
    "integrated_question",
    "interval_test",
    "repeat_deep_cause",
}

STAGE_LABELS = {
    0: "unlearned",
    1: "exposed",
    2: "initial_understanding",
    3: "recallable",
    4: "basic_application",
    5: "variant_application",
    6: "integrated_transfer",
    7: "stable_mastery",
    8: "decayed",
}


class MasteryServiceError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "MASTERY_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class MasteryGate:
    passed: bool
    blocking_reasons: list[str]
    evidence_ids: list[str]
    metrics: dict[str, Any]


@dataclass(frozen=True)
class MasteryEvaluation:
    knowledge_node_id: str
    previous_stage: int
    new_stage: int
    changed: bool
    rule_version: str
    evidence_ids: list[str]
    blocking_reasons: list[str]
    transition_reason: str
    next_action: str
    snapshot: MasterySnapshot | None
    remediation: dict[str, Any] | None


def create_mastery_evidence(
    session: Session,
    *,
    knowledge_node_id: str,
    evidence_type: EvidenceType,
    source_type: str,
    source_id: str | None = None,
    score: int | None = None,
    sample_count: int = 0,
    correct_count: int | None = None,
    accuracy: int | None = None,
    hint_level: int | None = None,
    is_original: bool = False,
    occurred_at: datetime | None = None,
    confirmed: bool = True,
    metadata_json: dict[str, Any] | None = None,
    created_by: str = "system",
) -> MasteryEvidence:
    get_knowledge_node(session, knowledge_node_id)
    _validate_evidence(
        evidence_type=evidence_type,
        score=score,
        sample_count=sample_count,
        correct_count=correct_count,
        accuracy=accuracy,
    )
    evidence = MasteryEvidence(
        id=str(uuid4()),
        knowledge_node_id=knowledge_node_id,
        evidence_type=evidence_type,
        source_type=source_type,
        source_id=source_id,
        score=score,
        sample_count=sample_count,
        correct_count=correct_count,
        accuracy=accuracy,
        hint_level=hint_level,
        is_original=is_original,
        occurred_at=occurred_at or utc_now(),
        confirmed=confirmed,
        metadata_json=metadata_json,
        created_by=created_by,
    )
    session.add(evidence)
    session.flush()
    return evidence


def list_mastery_evidence(session: Session, knowledge_node_id: str) -> list[MasteryEvidence]:
    get_knowledge_node(session, knowledge_node_id)
    return list(
        session.scalars(
            select(MasteryEvidence)
            .where(
                MasteryEvidence.knowledge_node_id == knowledge_node_id,
                MasteryEvidence.is_deleted.is_(False),
            )
            .order_by(MasteryEvidence.occurred_at, MasteryEvidence.created_at)
        ).all()
    )


def get_mastery_history(session: Session, knowledge_node_id: str) -> list[MasterySnapshot]:
    get_knowledge_node(session, knowledge_node_id)
    return list(
        session.scalars(
            select(MasterySnapshot)
            .where(MasterySnapshot.knowledge_node_id == knowledge_node_id)
            .order_by(literal_column("rowid"), MasterySnapshot.evaluated_at)
        ).all()
    )


def evaluate_mastery(
    session: Session,
    knowledge_node_id: str,
    *,
    target_stage: int | None = None,
    actor_type: str = "system",
) -> MasteryEvaluation:
    get_knowledge_node(session, knowledge_node_id)
    evidence = _confirmed_evidence(session, knowledge_node_id)
    current_snapshot = _latest_snapshot(session, knowledge_node_id)
    current_stage = current_snapshot.stage if current_snapshot is not None else 0

    regression = _regression_gate(current_stage, evidence)
    if regression is not None:
        return _create_snapshot_result(
            session,
            knowledge_node_id=knowledge_node_id,
            previous_stage=current_stage,
            new_stage=regression["stage"],
            gate=MasteryGate(
                passed=True,
                blocking_reasons=[],
                evidence_ids=regression["evidence_ids"],
                metrics=regression["metrics"],
            ),
            transition_reason=regression["reason"],
            actor_type=actor_type,
            remediation=regression["remediation"],
        )

    next_stage = target_stage if target_stage is not None else min(current_stage + 1, 7)
    _validate_stage(next_stage)
    if next_stage <= current_stage:
        return MasteryEvaluation(
            knowledge_node_id=knowledge_node_id,
            previous_stage=current_stage,
            new_stage=current_stage,
            changed=False,
            rule_version=MASTERY_RULE_VERSION,
            evidence_ids=[],
            blocking_reasons=[],
            transition_reason="already_at_or_above_target",
            next_action="no_action",
            snapshot=None,
            remediation=None,
        )
    if next_stage > current_stage + 1:
        return MasteryEvaluation(
            knowledge_node_id=knowledge_node_id,
            previous_stage=current_stage,
            new_stage=current_stage,
            changed=False,
            rule_version=MASTERY_RULE_VERSION,
            evidence_ids=[],
            blocking_reasons=["STAGE_SKIP_NOT_ALLOWED"],
            transition_reason="blocked",
            next_action=f"evaluate_stage_{current_stage + 1}_first",
            snapshot=None,
            remediation=None,
        )

    gate = _gate_for_stage(next_stage, evidence)
    if not gate.passed:
        return MasteryEvaluation(
            knowledge_node_id=knowledge_node_id,
            previous_stage=current_stage,
            new_stage=current_stage,
            changed=False,
            rule_version=MASTERY_RULE_VERSION,
            evidence_ids=gate.evidence_ids,
            blocking_reasons=gate.blocking_reasons,
            transition_reason="blocked",
            next_action=_next_action_for_blockers(gate.blocking_reasons),
            snapshot=None,
            remediation=None,
        )

    return _create_snapshot_result(
        session,
        knowledge_node_id=knowledge_node_id,
        previous_stage=current_stage,
        new_stage=next_stage,
        gate=gate,
        transition_reason=f"advanced_to_{STAGE_LABELS[next_stage]}",
        actor_type=actor_type,
        remediation=None,
    )


def rollback_mastery(
    session: Session,
    knowledge_node_id: str,
    *,
    target_stage: int,
    evidence_id: str,
    reason: str,
    actor_type: str = "system",
) -> MasteryEvaluation:
    get_knowledge_node(session, knowledge_node_id)
    _validate_stage(target_stage)
    evidence = session.get(MasteryEvidence, evidence_id)
    if evidence is None or evidence.knowledge_node_id != knowledge_node_id or evidence.is_deleted:
        raise MasteryServiceError(
            "mastery rollback evidence not found",
            code="MASTERY_EVIDENCE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"evidence_id": evidence_id},
        )
    current_snapshot = _latest_snapshot(session, knowledge_node_id)
    current_stage = current_snapshot.stage if current_snapshot is not None else 0
    if target_stage >= current_stage:
        raise MasteryServiceError(
            "mastery rollback target must be lower than current stage",
            code="MASTERY_ROLLBACK_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"current_stage": current_stage, "target_stage": target_stage},
        )
    return _create_snapshot_result(
        session,
        knowledge_node_id=knowledge_node_id,
        previous_stage=current_stage,
        new_stage=target_stage,
        gate=MasteryGate(
            passed=True,
            blocking_reasons=[],
            evidence_ids=[evidence.id],
            metrics={"rollback_reason": reason},
        ),
        transition_reason=reason,
        actor_type=actor_type,
        remediation={"priority": "high", "next_action": "create_remedial_task"},
    )


def _validate_evidence(
    *,
    evidence_type: str,
    score: int | None,
    sample_count: int,
    correct_count: int | None,
    accuracy: int | None,
) -> None:
    if evidence_type not in EVIDENCE_TYPES:
        raise MasteryServiceError(
            "unsupported mastery evidence type",
            code="MASTERY_EVIDENCE_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"evidence_type": evidence_type},
        )
    for field_name, value in {"score": score, "accuracy": accuracy}.items():
        if value is not None and not 0 <= value <= 100:
            raise MasteryServiceError(
                "mastery evidence score fields must be 0-100",
                code="MASTERY_EVIDENCE_SCORE_INVALID",
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                details={"field": field_name, "value": value},
            )
    if sample_count < 0 or (correct_count is not None and correct_count < 0):
        raise MasteryServiceError(
            "mastery evidence counts must not be negative",
            code="MASTERY_EVIDENCE_COUNT_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )


def _validate_stage(stage: int) -> None:
    if stage not in STAGE_LABELS:
        raise MasteryServiceError(
            "unsupported mastery stage",
            code="MASTERY_STAGE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"stage": stage},
        )


def _confirmed_evidence(session: Session, knowledge_node_id: str) -> list[MasteryEvidence]:
    return [
        item
        for item in list_mastery_evidence(session, knowledge_node_id)
        if item.confirmed and not item.is_deleted
    ]


def _latest_snapshot(session: Session, knowledge_node_id: str) -> MasterySnapshot | None:
    return session.scalar(
        select(MasterySnapshot)
        .where(MasterySnapshot.knowledge_node_id == knowledge_node_id)
        .order_by(literal_column("rowid").desc())
    )


def _gate_for_stage(stage: int, evidence: list[MasteryEvidence]) -> MasteryGate:
    if stage == 1:
        return _gate_exposed(evidence)
    if stage == 2:
        return _gate_score(
            evidence,
            evidence_type="self_explanation",
            score_field="score",
            minimum=70,
            missing_reason="MISSING_SELF_EXPLANATION",
            low_reason="SELF_EXPLANATION_SCORE_TOO_LOW",
        )
    if stage == 3:
        return _gate_recallable(evidence)
    if stage == 4:
        return _gate_question_practice(
            evidence,
            evidence_type="basic_question",
            minimum_samples=4,
            minimum_accuracy=75,
            missing_reason="MISSING_BASIC_QUESTION_EVIDENCE",
            sample_reason="BASIC_SAMPLE_COUNT_TOO_LOW",
            accuracy_reason="BASIC_ACCURACY_TOO_LOW",
        )
    if stage == 5:
        return _gate_variant(evidence)
    if stage == 6:
        return _gate_question_practice(
            evidence,
            evidence_type="integrated_question",
            minimum_samples=2,
            minimum_accuracy=65,
            missing_reason="MISSING_INTEGRATED_EVIDENCE",
            sample_reason="INTEGRATED_SAMPLE_COUNT_TOO_LOW",
            accuracy_reason="INTEGRATED_ACCURACY_TOO_LOW",
        )
    if stage == 7:
        return _gate_stable_mastery(evidence)
    return MasteryGate(
        passed=False,
        blocking_reasons=["DECAYED_STAGE_REQUIRES_ROLLBACK_TRIGGER"],
        evidence_ids=[],
        metrics={},
    )


def _gate_exposed(evidence: list[MasteryEvidence]) -> MasteryGate:
    if not evidence:
        return MasteryGate(False, ["NO_CONFIRMED_EVIDENCE"], [], {})
    return MasteryGate(True, [], [evidence[-1].id], {"evidence_count": len(evidence)})


def _gate_score(
    evidence: list[MasteryEvidence],
    *,
    evidence_type: str,
    score_field: str,
    minimum: int,
    missing_reason: str,
    low_reason: str,
) -> MasteryGate:
    candidates = [item for item in evidence if item.evidence_type == evidence_type]
    if not candidates:
        return MasteryGate(False, [missing_reason], [], {})
    best = max(candidates, key=lambda item: item.score or 0)
    score = best.score if score_field == "score" else best.accuracy
    if score is None or score < minimum:
        return MasteryGate(False, [low_reason], [best.id], {"score": score})
    return MasteryGate(True, [], [best.id], {"score": score})


def _gate_recallable(evidence: list[MasteryEvidence]) -> MasteryGate:
    candidates = [item for item in evidence if item.evidence_type == "closed_book_recall"]
    if not candidates:
        return MasteryGate(False, ["MISSING_CLOSED_BOOK_RECALL"], [], {})
    best = max(candidates, key=lambda item: item.score or 0)
    blockers = []
    if best.score is None or best.score < 70:
        blockers.append("CLOSED_BOOK_RECALL_SCORE_TOO_LOW")
    if best.hint_level is not None and best.hint_level > 1:
        blockers.append("HINT_LEVEL_TOO_HIGH")
    if blockers:
        return MasteryGate(
            False,
            blockers,
            [best.id],
            {"score": best.score, "hint_level": best.hint_level},
        )
    return MasteryGate(
        True,
        [],
        [best.id],
        {"score": best.score, "hint_level": best.hint_level},
    )


def _gate_question_practice(
    evidence: list[MasteryEvidence],
    *,
    evidence_type: str,
    minimum_samples: int,
    minimum_accuracy: int,
    missing_reason: str,
    sample_reason: str,
    accuracy_reason: str,
) -> MasteryGate:
    candidates = [item for item in evidence if item.evidence_type == evidence_type]
    if not candidates:
        return MasteryGate(False, [missing_reason], [], {})
    aggregate = _aggregate_questions(candidates)
    blockers = []
    if aggregate["sample_count"] < minimum_samples:
        blockers.append(sample_reason)
    if aggregate["accuracy"] < minimum_accuracy:
        blockers.append(accuracy_reason)
    if blockers:
        return MasteryGate(False, blockers, aggregate["evidence_ids"], aggregate)
    return MasteryGate(True, [], aggregate["evidence_ids"], aggregate)


def _gate_variant(evidence: list[MasteryEvidence]) -> MasteryGate:
    variant = [item for item in evidence if item.evidence_type == "variant_question"]
    if not variant:
        return MasteryGate(False, ["MISSING_VARIANT_EVIDENCE"], [], {})
    non_original = [item for item in variant if not item.is_original]
    if not non_original:
        return MasteryGate(
            False,
            ["VARIANT_REQUIRES_NON_ORIGINAL"],
            [item.id for item in variant],
            {"original_question_samples": sum(item.sample_count for item in variant)},
        )
    return _gate_question_practice(
        non_original,
        evidence_type="variant_question",
        minimum_samples=3,
        minimum_accuracy=70,
        missing_reason="MISSING_VARIANT_EVIDENCE",
        sample_reason="VARIANT_SAMPLE_COUNT_TOO_LOW",
        accuracy_reason="VARIANT_ACCURACY_TOO_LOW",
    )


def _gate_stable_mastery(evidence: list[MasteryEvidence]) -> MasteryGate:
    if any(item.evidence_type == "repeat_deep_cause" for item in evidence):
        return MasteryGate(False, ["UNRESOLVED_REPEAT_DEEP_CAUSE"], [], {})
    recall = _best_score(evidence, "closed_book_recall")
    basic = _aggregate_questions(
        [item for item in evidence if item.evidence_type == "basic_question"]
    )
    variant = _aggregate_questions(
        [
            item
            for item in evidence
            if item.evidence_type == "variant_question" and not item.is_original
        ]
    )
    transfer = _aggregate_questions(
        [item for item in evidence if item.evidence_type == "integrated_question"]
    )
    distinct_dates = {item.occurred_at.date().isoformat() for item in evidence}
    blockers = []
    if len(distinct_dates) < 2:
        blockers.append("STABLE_REQUIRES_MULTIPLE_TIMEPOINTS")
    if (recall["score"] or 0) < 80:
        blockers.append("STABLE_RECALL_SCORE_TOO_LOW")
    if basic["accuracy"] < 80:
        blockers.append("STABLE_BASIC_SCORE_TOO_LOW")
    if variant["accuracy"] < 75:
        blockers.append("STABLE_VARIANT_SCORE_TOO_LOW")
    if transfer["accuracy"] < 70:
        blockers.append("STABLE_TRANSFER_SCORE_TOO_LOW")
    evidence_ids = sorted(
        set(
            recall["evidence_ids"]
            + basic["evidence_ids"]
            + variant["evidence_ids"]
            + transfer["evidence_ids"]
        )
    )
    metrics = {
        "distinct_timepoints": len(distinct_dates),
        "recall_score": recall["score"],
        "basic_score": basic["accuracy"],
        "variant_score": variant["accuracy"],
        "transfer_score": transfer["accuracy"],
    }
    return MasteryGate(not blockers, blockers, evidence_ids, metrics)


def _aggregate_questions(items: list[MasteryEvidence]) -> dict[str, Any]:
    sample_count = sum(item.sample_count for item in items)
    correct_count = 0
    for item in items:
        if item.correct_count is not None:
            correct_count += item.correct_count
        elif item.accuracy is not None:
            correct_count += round(item.sample_count * item.accuracy / 100)
    accuracy = round(correct_count * 100 / sample_count) if sample_count else 0
    return {
        "sample_count": sample_count,
        "correct_count": correct_count,
        "accuracy": accuracy,
        "evidence_ids": [item.id for item in items],
    }


def _best_score(evidence: list[MasteryEvidence], evidence_type: str) -> dict[str, Any]:
    candidates = [item for item in evidence if item.evidence_type == evidence_type]
    if not candidates:
        return {"score": None, "evidence_ids": []}
    best = max(candidates, key=lambda item: item.score or 0)
    return {"score": best.score, "evidence_ids": [best.id]}


def _regression_gate(
    current_stage: int,
    evidence: list[MasteryEvidence],
) -> dict[str, Any] | None:
    repeat = _latest_evidence_of_type(evidence, "repeat_deep_cause")
    if repeat is not None and current_stage >= 5:
        return {
            "stage": 4,
            "evidence_ids": [repeat.id],
            "metrics": {"repeat_deep_cause": True},
            "reason": "repeat_deep_cause_regression",
            "remediation": {"priority": "high", "next_action": "create_remedial_task"},
        }
    interval = _latest_evidence_of_type(evidence, "interval_test")
    interval_score = _evidence_score(interval)
    if interval is not None and current_stage >= 7 and interval_score < 70:
        return {
            "stage": 8,
            "evidence_ids": [interval.id],
            "metrics": {"interval_score": interval_score},
            "reason": "interval_test_failed",
            "remediation": {"priority": "high", "next_action": "schedule_short_interval_review"},
        }
    return None


def _latest_evidence_of_type(
    evidence: list[MasteryEvidence],
    evidence_type: str,
) -> MasteryEvidence | None:
    candidates = [item for item in evidence if item.evidence_type == evidence_type]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.occurred_at)


def _evidence_score(evidence: MasteryEvidence | None) -> int:
    if evidence is None:
        return 100
    if evidence.score is not None:
        return evidence.score
    if evidence.accuracy is not None:
        return evidence.accuracy
    return 0


def _create_snapshot_result(
    session: Session,
    *,
    knowledge_node_id: str,
    previous_stage: int,
    new_stage: int,
    gate: MasteryGate,
    transition_reason: str,
    actor_type: str,
    remediation: dict[str, Any] | None,
) -> MasteryEvaluation:
    snapshot = MasterySnapshot(
        id=str(uuid4()),
        knowledge_node_id=knowledge_node_id,
        previous_stage=previous_stage,
        stage=new_stage,
        recall_score=_metric_int(gate.metrics.get("recall_score") or gate.metrics.get("score")),
        basic_score=_metric_int(gate.metrics.get("basic_score")),
        variant_score=_metric_int(gate.metrics.get("variant_score")),
        transfer_score=_metric_int(gate.metrics.get("transfer_score")),
        retention_score=_metric_int(gate.metrics.get("interval_score")),
        repeat_error_rate=100 if gate.metrics.get("repeat_deep_cause") else None,
        confidence_calibration=None,
        missing_link=None,
        evaluated_at=utc_now(),
        rule_version=MASTERY_RULE_VERSION,
        transition_reason=transition_reason,
        evidence_ids_json=gate.evidence_ids,
        computed_metrics_json=gate.metrics,
        blocking_reasons_json=gate.blocking_reasons,
        remediation_json=remediation,
        actor_type=actor_type,
    )
    session.add(snapshot)
    session.flush()
    return MasteryEvaluation(
        knowledge_node_id=knowledge_node_id,
        previous_stage=previous_stage,
        new_stage=new_stage,
        changed=new_stage != previous_stage,
        rule_version=MASTERY_RULE_VERSION,
        evidence_ids=gate.evidence_ids,
        blocking_reasons=gate.blocking_reasons,
        transition_reason=transition_reason,
        next_action="continue" if remediation is None else str(remediation["next_action"]),
        snapshot=snapshot,
        remediation=remediation,
    )


def _metric_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _next_action_for_blockers(blockers: list[str]) -> str:
    if not blockers:
        return "continue"
    return f"collect_evidence:{blockers[0]}"
