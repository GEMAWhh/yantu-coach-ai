from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.base import utc_now
from app.models.evidence import AIJob
from app.models.knowledge import KnowledgeNode
from app.models.wrongbook import (
    Attempt,
    Question,
    QuestionAsset,
    WrongbookDraft,
    WrongRecord,
    WrongVerification,
)
from app.planning.engine import PlanningCandidate
from app.services.audit import write_audit_event

WRONGBOOK_SCHEMA_VERSION = "wrongbook-analysis-v1"
FAKE_PROVIDER = "fake"
FAKE_MODEL_NAME = "fake-wrongbook-provider"
FAKE_PROMPT_VERSION = "wrongbook-draft-fake-v1"

AssetRole = Literal[
    "statement",
    "figure",
    "my_answer",
    "marking",
    "standard_answer",
    "original_solution",
    "supplement",
]
AttemptType = Literal[
    "original_redo",
    "no_hint_redo",
    "variant",
    "interval_test",
    "transfer_test",
]
WrongStatus = Literal[
    "pending_analysis",
    "pending_no_hint_redo",
    "pending_variant",
    "pending_interval",
    "stable_corrected",
    "regressed",
]
ProviderMode = Literal["valid", "invalid_schema"]

ASSET_ROLES = {
    "statement",
    "figure",
    "my_answer",
    "marking",
    "standard_answer",
    "original_solution",
    "supplement",
}
ATTEMPT_TYPES = {
    "original_redo",
    "no_hint_redo",
    "variant",
    "interval_test",
    "transfer_test",
}
WRONG_STATUSES = {
    "pending_analysis",
    "pending_no_hint_redo",
    "pending_variant",
    "pending_interval",
    "stable_corrected",
    "regressed",
}
REQUIRED_CORRECTION_ATTEMPTS = {"no_hint_redo", "variant", "interval_test"}


class WrongbookError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "WRONGBOOK_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class AttemptSubmission:
    attempt: Attempt
    wrong_record: WrongRecord
    verification: WrongVerification
    created: bool


@dataclass(frozen=True)
class WrongbookConfirmation:
    wrong_record: WrongRecord
    draft: WrongbookDraft
    created: bool


def create_question(
    session: Session,
    *,
    standard_text: str,
    subject_id: str | None = None,
    knowledge_node_id: str | None = None,
    question_type: str | None = None,
    difficulty: str | None = None,
    source: str | None = None,
    source_year: int | None = None,
    source_page: str | None = None,
    status: str = "active",
    created_by: str = "system",
) -> Question:
    if knowledge_node_id is not None:
        knowledge = _get_knowledge_node(session, knowledge_node_id)
        subject_id = subject_id or knowledge.subject_id
    question = Question(
        id=str(uuid4()),
        standard_text=standard_text,
        subject_id=subject_id,
        knowledge_node_id=knowledge_node_id,
        question_type=question_type,
        difficulty=difficulty,
        source=source,
        source_year=source_year,
        source_page=source_page,
        status=status,
        created_by=created_by,
    )
    session.add(question)
    session.flush()
    return question


def get_question(session: Session, question_id: str, *, include_deleted: bool = False) -> Question:
    question = session.get(Question, question_id)
    if question is None or (question.is_deleted and not include_deleted):
        raise WrongbookError(
            "question not found",
            code="QUESTION_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"question_id": question_id},
        )
    return question


def create_wrong_record(
    session: Session,
    *,
    question_id: str,
    knowledge_node_id: str | None = None,
    surface_cause: str | None = None,
    deep_cause: str | None = None,
    prerequisite_gap: str | None = None,
    error_count: int = 1,
    next_review_at: datetime | None = None,
    created_by: str = "system",
) -> WrongRecord:
    question = get_question(session, question_id)
    resolved_knowledge_id = knowledge_node_id or question.knowledge_node_id
    if resolved_knowledge_id is not None:
        _get_knowledge_node(session, resolved_knowledge_id)
    if error_count < 1:
        raise WrongbookError(
            "wrong record error_count must be at least one",
            code="WRONG_RECORD_ERROR_COUNT_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"error_count": error_count},
        )
    initial_status = (
        "pending_no_hint_redo"
        if surface_cause and deep_cause and prerequisite_gap
        else "pending_analysis"
    )
    wrong = WrongRecord(
        id=str(uuid4()),
        question_id=question.id,
        knowledge_node_id=resolved_knowledge_id,
        surface_cause=surface_cause,
        deep_cause=deep_cause,
        prerequisite_gap=prerequisite_gap,
        error_count=error_count,
        redo_count=0,
        current_status=initial_status,
        next_review_at=next_review_at,
        created_by=created_by,
    )
    session.add(wrong)
    session.flush()
    session.add(WrongVerification(id=str(uuid4()), wrong_record_id=wrong.id))
    session.flush()
    return wrong


def get_wrong_record(session: Session, wrong_record_id: str) -> WrongRecord:
    wrong = session.get(WrongRecord, wrong_record_id)
    if wrong is None:
        raise WrongbookError(
            "wrong record not found",
            code="WRONG_RECORD_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"wrong_record_id": wrong_record_id},
        )
    return wrong


def get_wrong_verification(session: Session, wrong_record_id: str) -> WrongVerification:
    get_wrong_record(session, wrong_record_id)
    verification = session.scalar(
        select(WrongVerification).where(WrongVerification.wrong_record_id == wrong_record_id)
    )
    if verification is None:
        verification = WrongVerification(id=str(uuid4()), wrong_record_id=wrong_record_id)
        session.add(verification)
        session.flush()
    return verification


def list_wrong_attempts(session: Session, wrong_record_id: str) -> list[Attempt]:
    wrong = get_wrong_record(session, wrong_record_id)
    return list(
        session.scalars(
            select(Attempt)
            .where(Attempt.wrong_record_id == wrong.id)
            .order_by(Attempt.attempted_at, Attempt.created_at, Attempt.id)
        ).all()
    )


def analyze_wrong_record(
    session: Session,
    wrong_record_id: str,
    *,
    provider_mode: ProviderMode = "valid",
) -> WrongbookDraft:
    wrong = get_wrong_record(session, wrong_record_id)
    question = get_question(session, wrong.question_id)
    asset_ids = _asset_ids_for_question(session, question.id)
    started_at = utc_now()
    output = _fake_provider_output(wrong, question, asset_ids, provider_mode)
    validation_errors = validate_wrongbook_payload(output)
    job_status = "succeeded" if not validation_errors else "failed"
    job = AIJob(
        id=str(uuid4()),
        job_type="wrongbook_analysis",
        provider=FAKE_PROVIDER,
        model_name=FAKE_MODEL_NAME,
        prompt_version=FAKE_PROMPT_VERSION,
        status=job_status,
        attempts=1,
        input_json={
            "wrong_record_id": wrong.id,
            "question_id": question.id,
            "asset_ids": asset_ids,
        },
        output_json=output,
        error_code=None if not validation_errors else "AI_OUTPUT_SCHEMA_INVALID",
        error_message=None if not validation_errors else "; ".join(validation_errors),
        started_at=started_at,
        completed_at=utc_now(),
    )
    session.add(job)
    session.flush()
    draft = WrongbookDraft(
        id=str(uuid4()),
        wrong_record_id=wrong.id,
        ai_job_id=job.id,
        status="draft" if not validation_errors else "needs_correction",
        schema_version=WRONGBOOK_SCHEMA_VERSION,
        structured_json=output,
        validation_errors_json=validation_errors,
    )
    session.add(draft)
    session.flush()
    return draft


def get_wrongbook_draft(session: Session, wrong_record_id: str) -> WrongbookDraft:
    get_wrong_record(session, wrong_record_id)
    draft = session.scalar(
        select(WrongbookDraft)
        .where(WrongbookDraft.wrong_record_id == wrong_record_id)
        .order_by(literal_column("rowid").desc())
    )
    if draft is None:
        raise WrongbookError(
            "wrongbook draft not found",
            code="WRONGBOOK_DRAFT_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"wrong_record_id": wrong_record_id},
        )
    return draft


def update_wrongbook_draft(
    session: Session,
    wrong_record_id: str,
    *,
    structured_json: dict[str, Any],
) -> WrongbookDraft:
    draft = get_wrongbook_draft(session, wrong_record_id)
    if draft.status == "confirmed":
        raise WrongbookError(
            "confirmed wrongbook draft cannot be edited",
            code="WRONGBOOK_DRAFT_FINALIZED",
            status_code=HTTPStatus.CONFLICT,
            details={"draft_id": draft.id, "status": draft.status},
        )
    validation_errors = validate_wrongbook_payload(structured_json)
    draft.structured_json = structured_json
    draft.validation_errors_json = validation_errors
    draft.status = "draft" if not validation_errors else "needs_correction"
    session.flush()
    return draft


def confirm_wrongbook_draft(
    session: Session,
    wrong_record_id: str,
    *,
    request_id: str | None = None,
    actor_type: str = "system",
) -> WrongbookConfirmation:
    wrong = get_wrong_record(session, wrong_record_id)
    draft = get_wrongbook_draft(session, wrong.id)
    if draft.status == "confirmed":
        return WrongbookConfirmation(wrong_record=wrong, draft=draft, created=False)
    if draft.status != "draft":
        raise WrongbookError(
            "only valid wrongbook draft can be confirmed",
            code="AI_DRAFT_NOT_CONFIRMED",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"draft_id": draft.id, "status": draft.status},
        )
    payload = draft.structured_json
    wrong.surface_cause = payload["surface_cause"]
    wrong.deep_cause = payload["deep_cause"]
    wrong.prerequisite_gap = payload["prerequisite_gap"]
    if wrong.current_status == "pending_analysis":
        wrong.current_status = "pending_no_hint_redo"
    now = utc_now()
    draft.status = "confirmed"
    draft.confirmed_at = now
    draft.confirmed_once = True
    write_audit_event(
        session,
        event_type="wrongbook.draft_confirmed",
        actor_type=actor_type,
        object_type="wrong_record",
        object_id=wrong.id,
        after_json={
            "draft_id": draft.id,
            "schema_version": draft.schema_version,
            "surface_cause": wrong.surface_cause,
            "deep_cause": wrong.deep_cause,
            "prerequisite_gap": wrong.prerequisite_gap,
        },
        reason="confirmed wrongbook draft into formal wrong record",
        request_id=request_id,
    )
    session.flush()
    return WrongbookConfirmation(wrong_record=wrong, draft=draft, created=True)


def validate_wrongbook_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "surface_cause",
        "deep_cause",
        "prerequisite_gap",
        "remediation_plan",
        "uncertain_fields",
    }
    extra = set(payload) - required
    missing = required - set(payload)
    errors.extend(f"missing:{field}" for field in sorted(missing))
    errors.extend(f"extra:{field}" for field in sorted(extra))
    for field in ("surface_cause", "deep_cause", "prerequisite_gap"):
        if field in payload and not isinstance(payload[field], str):
            errors.append(f"type:{field}")
    _validate_remediation_plan(payload.get("remediation_plan"), errors)
    _validate_uncertain_fields(payload.get("uncertain_fields"), errors)
    return errors


def link_question_asset(
    session: Session,
    *,
    wrong_record_id: str,
    asset_id: str,
    asset_role: AssetRole,
    page_order: int = 0,
) -> QuestionAsset:
    _validate_asset_role(asset_role)
    wrong = get_wrong_record(session, wrong_record_id)
    if session.get(Asset, asset_id) is None:
        raise WrongbookError(
            "asset not found",
            code="ASSET_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"asset_id": asset_id},
        )
    if page_order < 0:
        raise WrongbookError(
            "question asset page_order must not be negative",
            code="QUESTION_ASSET_PAGE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"page_order": page_order},
        )
    existing = session.scalar(
        select(QuestionAsset).where(
            QuestionAsset.question_id == wrong.question_id,
            QuestionAsset.asset_role == asset_role,
            QuestionAsset.page_order == page_order,
        )
    )
    if existing is not None:
        raise WrongbookError(
            "question asset role and page_order already exists",
            code="QUESTION_ASSET_DUPLICATE_ROLE_PAGE",
            status_code=HTTPStatus.CONFLICT,
            details={"asset_role": asset_role, "page_order": page_order},
        )
    question_asset = QuestionAsset(
        id=str(uuid4()),
        question_id=wrong.question_id,
        asset_id=asset_id,
        asset_role=asset_role,
        page_order=page_order,
    )
    session.add(question_asset)
    session.flush()
    return question_asset


def submit_attempt(
    session: Session,
    wrong_record_id: str,
    *,
    attempt_type: AttemptType,
    is_correct: bool,
    attempted_at: datetime | None = None,
    answer_text: str | None = None,
    score: int | None = None,
    duration_seconds: int | None = None,
    hint_level: int | None = None,
    confidence: int | None = None,
    idempotency_key: str | None = None,
    request_id: str | None = None,
    created_by: str = "system",
) -> AttemptSubmission:
    _validate_attempt_type(attempt_type)
    _validate_optional_range("score", score, minimum=0, maximum=100)
    _validate_optional_non_negative("duration_seconds", duration_seconds)
    _validate_optional_non_negative("hint_level", hint_level)
    _validate_optional_range("confidence", confidence, minimum=0, maximum=100)
    wrong = get_wrong_record(session, wrong_record_id)
    verification = get_wrong_verification(session, wrong.id)
    if idempotency_key:
        existing = session.scalar(
            select(Attempt).where(
                Attempt.wrong_record_id == wrong.id,
                Attempt.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return AttemptSubmission(
                attempt=existing,
                wrong_record=wrong,
                verification=verification,
                created=False,
            )
    occurred_at = attempted_at or utc_now()
    attempt = Attempt(
        id=str(uuid4()),
        question_id=wrong.question_id,
        wrong_record_id=wrong.id,
        idempotency_key=idempotency_key,
        attempt_type=attempt_type,
        attempted_at=occurred_at,
        answer_text=answer_text,
        is_correct=is_correct,
        score=score,
        duration_seconds=duration_seconds,
        hint_level=hint_level,
        confidence=confidence,
        request_id=request_id,
        created_by=created_by,
    )
    session.add(attempt)
    session.flush()
    _apply_attempt_result(wrong, verification, attempt)
    write_audit_event(
        session,
        event_type="wrongbook.attempt_submitted",
        actor_type=created_by,
        object_type="wrong_record",
        object_id=wrong.id,
        after_json={
            "attempt_id": attempt.id,
            "attempt_type": attempt.attempt_type,
            "is_correct": attempt.is_correct,
            "current_status": wrong.current_status,
            "error_count": wrong.error_count,
        },
        reason="wrongbook deterministic verification state updated",
        request_id=request_id,
    )
    session.flush()
    return AttemptSubmission(
        attempt=attempt,
        wrong_record=wrong,
        verification=verification,
        created=True,
    )


def list_wrongbook_planning_candidates(session: Session) -> list[PlanningCandidate]:
    rows = session.execute(
        select(WrongRecord, Question)
        .join(Question, WrongRecord.question_id == Question.id)
        .where(
            WrongRecord.current_status != "stable_corrected",
            Question.is_deleted.is_(False),
        )
        .order_by(WrongRecord.updated_at.desc())
    ).all()
    candidates: list[PlanningCandidate] = []
    for wrong, question in rows:
        knowledge = (
            session.get(KnowledgeNode, wrong.knowledge_node_id)
            if wrong.knowledge_node_id is not None
            else None
        )
        subject_id = question.subject_id or (
            knowledge.subject_id if knowledge is not None else None
        )
        candidates.append(
            PlanningCandidate(
                id=f"wrong:{wrong.id}",
                title=f"Wrongbook remediation: {_short_text(question.standard_text)}",
                subject_id=subject_id or "unknown",
                estimated_minutes=25,
                cognitive_load="medium",
                prerequisite_status="satisfied",
                source_type="wrong_record",
                source_id=wrong.id,
                task_type="wrongbook_remediation",
                difficulty=question.difficulty,
                review_due=80 if wrong.current_status in {"pending_interval", "regressed"} else 45,
                knowledge_importance=(
                    knowledge.importance
                    if knowledge is not None and knowledge.importance is not None
                    else 50
                ),
                weakness=min(100, wrong.error_count * 25),
                repeat_error=min(100, wrong.error_count * 20),
                energy_fit=70,
            )
        )
    return candidates


def _apply_attempt_result(
    wrong: WrongRecord,
    verification: WrongVerification,
    attempt: Attempt,
) -> None:
    wrong.redo_count += 1
    verification.last_attempt_id = attempt.id
    if not attempt.is_correct:
        wrong.error_count += 1
        wrong.current_status = "regressed"
        wrong.resolved_at = None
        _set_attempt_flag(verification, attempt.attempt_type, False)
        return
    _set_attempt_flag(verification, attempt.attempt_type, True)
    _recalculate_wrong_status(wrong, verification, attempt.attempted_at)


def _recalculate_wrong_status(
    wrong: WrongRecord,
    verification: WrongVerification,
    resolved_at: datetime,
) -> None:
    if (
        verification.no_hint_redo_passed
        and verification.variant_passed
        and verification.interval_test_passed
    ):
        wrong.current_status = "stable_corrected"
        wrong.resolved_at = resolved_at
        return
    wrong.resolved_at = None
    if verification.no_hint_redo_passed and verification.variant_passed:
        wrong.current_status = "pending_interval"
        return
    if (
        verification.original_redo_passed
        or verification.no_hint_redo_passed
        or verification.variant_passed
    ):
        wrong.current_status = "pending_variant"
        return
    wrong.current_status = "pending_no_hint_redo"


def _set_attempt_flag(
    verification: WrongVerification,
    attempt_type: str,
    value: bool,
) -> None:
    if attempt_type == "original_redo":
        verification.original_redo_passed = value
    elif attempt_type == "no_hint_redo":
        verification.no_hint_redo_passed = value
    elif attempt_type == "variant":
        verification.variant_passed = value
    elif attempt_type == "interval_test":
        verification.interval_test_passed = value
    elif attempt_type == "transfer_test":
        verification.transfer_test_passed = value


def _get_knowledge_node(session: Session, knowledge_node_id: str) -> KnowledgeNode:
    knowledge = session.get(KnowledgeNode, knowledge_node_id)
    if knowledge is None or knowledge.is_deleted:
        raise WrongbookError(
            "knowledge node not found",
            code="KNOWLEDGE_NODE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"knowledge_node_id": knowledge_node_id},
        )
    return knowledge


def _validate_asset_role(asset_role: str) -> None:
    if asset_role not in ASSET_ROLES:
        raise WrongbookError(
            "unsupported question asset role",
            code="QUESTION_ASSET_ROLE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"asset_role": asset_role, "allowed": sorted(ASSET_ROLES)},
        )


def _validate_attempt_type(attempt_type: str) -> None:
    if attempt_type not in ATTEMPT_TYPES:
        raise WrongbookError(
            "unsupported wrongbook attempt type",
            code="WRONG_ATTEMPT_TYPE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"attempt_type": attempt_type, "allowed": sorted(ATTEMPT_TYPES)},
        )


def _validate_optional_non_negative(field_name: str, value: int | None) -> None:
    if value is not None and value < 0:
        raise WrongbookError(
            "wrongbook numeric fields must not be negative",
            code="WRONGBOOK_VALUE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"field": field_name, "value": value},
        )


def _validate_optional_range(
    field_name: str,
    value: int | None,
    *,
    minimum: int,
    maximum: int,
) -> None:
    if value is not None and (value < minimum or value > maximum):
        raise WrongbookError(
            "wrongbook numeric fields are outside allowed range",
            code="WRONGBOOK_VALUE_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={
                "field": field_name,
                "value": value,
                "minimum": minimum,
                "maximum": maximum,
            },
        )


def _validate_remediation_plan(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("type:remediation_plan")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"type:remediation_plan[{index}]")
            continue
        extra = set(item) - {"action", "reason", "priority"}
        errors.extend(f"extra:remediation_plan[{index}].{field}" for field in sorted(extra))
        for field in ("action", "reason", "priority"):
            if field not in item:
                errors.append(f"missing:remediation_plan[{index}].{field}")
            elif not isinstance(item[field], str):
                errors.append(f"type:remediation_plan[{index}].{field}")


def _validate_uncertain_fields(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("type:uncertain_fields")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"type:uncertain_fields[{index}]")
            continue
        extra = set(item) - {"field", "reason", "confidence"}
        errors.extend(f"extra:uncertain_fields[{index}].{field}" for field in sorted(extra))
        for field in ("field", "reason", "confidence"):
            if field not in item:
                errors.append(f"missing:uncertain_fields[{index}].{field}")
        for field in ("field", "reason"):
            if field in item and not isinstance(item[field], str):
                errors.append(f"type:uncertain_fields[{index}].{field}")
        confidence = item.get("confidence")
        if (
            not isinstance(confidence, int | float)
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            errors.append(f"range:uncertain_fields[{index}].confidence")


def _fake_provider_output(
    wrong: WrongRecord,
    question: Question,
    asset_ids: list[str],
    provider_mode: ProviderMode,
) -> dict[str, Any]:
    if provider_mode == "invalid_schema":
        return {"surface_cause": "calculation slip"}
    return {
        "surface_cause": wrong.surface_cause or "answer process mismatch",
        "deep_cause": wrong.deep_cause or "core method was not retrieved without cues",
        "prerequisite_gap": wrong.prerequisite_gap or "prerequisite concept needs targeted review",
        "remediation_plan": [
            {
                "action": "redo_without_hints",
                "reason": f"question:{question.id}",
                "priority": "high",
            },
            {
                "action": "variant_practice",
                "reason": f"asset_count:{len(asset_ids)}",
                "priority": "normal",
            },
        ],
        "uncertain_fields": [
            {
                "field": "image_content",
                "reason": "fake provider does not inspect attached image or PDF content",
                "confidence": 0.25,
            }
        ],
    }


def _asset_ids_for_question(session: Session, question_id: str) -> list[str]:
    return list(
        session.scalars(
            select(QuestionAsset.asset_id)
            .where(QuestionAsset.question_id == question_id)
            .order_by(QuestionAsset.page_order)
        ).all()
    )


def _short_text(value: str, limit: int = 80) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."
