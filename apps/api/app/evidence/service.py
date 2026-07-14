import base64
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.files.storage import store_original_file
from app.models.asset import Asset
from app.models.base import utc_now
from app.models.evidence import AIJob, EvidenceAsset, EvidenceDraft, EvidenceRecord
from app.services.audit import write_audit_event
from app.settings import RuntimeSettings

EVIDENCE_SCHEMA_VERSION = "evidence-analysis-v1"
FAKE_PROVIDER = "fake"
FAKE_MODEL_NAME = "fake-evidence-provider"
FAKE_PROMPT_VERSION = "evidence-draft-fake-v1"

ProviderMode = Literal["valid", "invalid_schema"]


class EvidenceError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "EVIDENCE_ERROR",
        status_code: int = HTTPStatus.BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class EvidenceFileInput:
    original_name: str
    mime_type: str
    content_base64: str


@dataclass(frozen=True)
class EvidenceUpload:
    record: EvidenceRecord
    assets: list[Asset]


@dataclass(frozen=True)
class EvidenceConfirmation:
    record: EvidenceRecord
    draft: EvidenceDraft
    created: bool


def upload_evidence_files(
    settings: RuntimeSettings,
    session: Session,
    *,
    study_date: date,
    files: list[EvidenceFileInput],
    subject_id: str | None = None,
    created_by: str = "system",
) -> EvidenceUpload:
    if not files:
        raise EvidenceError(
            "evidence upload requires at least one file",
            code="EVIDENCE_FILE_REQUIRED",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    record = EvidenceRecord(
        id=str(uuid4()),
        study_date=study_date,
        subject_id=subject_id,
        status="pending",
        asset_count=len(files),
        created_by=created_by,
    )
    session.add(record)
    session.flush()

    assets: list[Asset] = []
    for index, file in enumerate(files):
        source_path = _write_upload_to_cache(settings, file)
        try:
            asset = store_original_file(
                settings,
                session,
                source_path=source_path,
                original_name=file.original_name,
                declared_mime_type=file.mime_type,
                state="inbox",
            )
        finally:
            source_path.unlink(missing_ok=True)
        session.flush()
        link = EvidenceAsset(
            id=str(uuid4()),
            evidence_record_id=record.id,
            asset_id=asset.id,
            page_order=index,
        )
        session.add(link)
        assets.append(asset)
    session.flush()
    return EvidenceUpload(record=record, assets=assets)


def analyze_evidence_record(
    session: Session,
    record_id: str,
    *,
    provider_mode: ProviderMode = "valid",
) -> EvidenceDraft:
    record = get_evidence_record(session, record_id)
    asset_ids = _asset_ids_for_record(session, record.id)
    started_at = utc_now()
    output = _fake_provider_output(record, asset_ids, provider_mode)
    validation_errors = validate_evidence_payload(output)
    job_status = "succeeded" if not validation_errors else "failed"
    job = AIJob(
        id=str(uuid4()),
        job_type="evidence_analysis",
        provider=FAKE_PROVIDER,
        model_name=FAKE_MODEL_NAME,
        prompt_version=FAKE_PROMPT_VERSION,
        status=job_status,
        attempts=1,
        input_json={"record_id": record.id, "asset_ids": asset_ids},
        output_json=output,
        error_code=None if not validation_errors else "AI_OUTPUT_SCHEMA_INVALID",
        error_message=None if not validation_errors else "; ".join(validation_errors),
        started_at=started_at,
        completed_at=utc_now(),
    )
    session.add(job)
    session.flush()
    draft = EvidenceDraft(
        id=str(uuid4()),
        evidence_record_id=record.id,
        ai_job_id=job.id,
        status="draft" if not validation_errors else "needs_correction",
        schema_version=EVIDENCE_SCHEMA_VERSION,
        structured_json=output,
        validation_errors_json=validation_errors,
    )
    session.add(draft)
    session.flush()
    return draft


def get_evidence_record(session: Session, record_id: str) -> EvidenceRecord:
    record = session.get(EvidenceRecord, record_id)
    if record is None:
        raise EvidenceError(
            "evidence record not found",
            code="EVIDENCE_RECORD_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"record_id": record_id},
        )
    return record


def get_evidence_draft(session: Session, record_id: str) -> EvidenceDraft:
    get_evidence_record(session, record_id)
    draft = session.scalar(
        select(EvidenceDraft)
        .where(EvidenceDraft.evidence_record_id == record_id)
        .order_by(literal_column("rowid").desc())
    )
    if draft is None:
        raise EvidenceError(
            "evidence draft not found",
            code="EVIDENCE_DRAFT_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"record_id": record_id},
        )
    return draft


def update_evidence_draft(
    session: Session,
    record_id: str,
    *,
    structured_json: dict[str, Any],
) -> EvidenceDraft:
    draft = get_evidence_draft(session, record_id)
    if draft.status in {"confirmed", "rejected"}:
        raise EvidenceError(
            "finalized evidence draft cannot be edited",
            code="EVIDENCE_DRAFT_FINALIZED",
            status_code=HTTPStatus.CONFLICT,
            details={"draft_id": draft.id, "status": draft.status},
        )
    validation_errors = validate_evidence_payload(structured_json)
    draft.structured_json = structured_json
    draft.validation_errors_json = validation_errors
    draft.status = "draft" if not validation_errors else "needs_correction"
    session.flush()
    return draft


def confirm_evidence_draft(
    session: Session,
    record_id: str,
    *,
    request_id: str | None = None,
    actor_type: str = "system",
) -> EvidenceConfirmation:
    record = get_evidence_record(session, record_id)
    draft = get_evidence_draft(session, record.id)
    if record.status == "confirmed":
        return EvidenceConfirmation(record=record, draft=draft, created=False)
    if draft.status != "draft":
        raise EvidenceError(
            "only valid draft can be confirmed",
            code="EVIDENCE_DRAFT_NOT_CONFIRMABLE",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"draft_id": draft.id, "status": draft.status},
        )
    payload = draft.structured_json
    record.status = "confirmed"
    record.confirmed_facts_json = payload["confirmed_facts"]
    record.inferences_json = payload["inferences"]
    record.uncertain_fields_json = payload["uncertain_fields"]
    record.teaching_judgment_json = payload["teaching_judgment"]
    record.suggested_actions_json = payload["suggested_actions"]
    record.confirmed_at = utc_now()
    draft.status = "confirmed"
    draft.confirmed_at = record.confirmed_at
    draft.confirmed_once = True
    write_audit_event(
        session,
        event_type="evidence.confirmed",
        actor_type=actor_type,
        object_type="evidence_record",
        object_id=record.id,
        after_json={"draft_id": draft.id, "schema_version": draft.schema_version},
        reason="confirmed evidence draft into formal record",
        request_id=request_id,
    )
    session.flush()
    return EvidenceConfirmation(record=record, draft=draft, created=True)


def reject_evidence_draft(
    session: Session,
    record_id: str,
    *,
    reason: str,
) -> EvidenceDraft:
    record = get_evidence_record(session, record_id)
    draft = get_evidence_draft(session, record.id)
    if draft.status == "confirmed":
        raise EvidenceError(
            "confirmed evidence draft cannot be rejected",
            code="EVIDENCE_DRAFT_FINALIZED",
            status_code=HTTPStatus.CONFLICT,
        )
    now = utc_now()
    draft.status = "rejected"
    draft.rejected_at = now
    draft.rejection_reason = reason
    record.status = "rejected"
    record.rejected_at = now
    session.flush()
    return draft


def validate_evidence_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "confirmed_facts",
        "inferences",
        "uncertain_fields",
        "teaching_judgment",
        "suggested_actions",
    }
    extra = set(payload) - required
    missing = required - set(payload)
    errors.extend(f"missing:{field}" for field in sorted(missing))
    errors.extend(f"extra:{field}" for field in sorted(extra))
    if "confirmed_facts" in payload and not isinstance(payload["confirmed_facts"], dict):
        errors.append("type:confirmed_facts")
    if "inferences" in payload and not isinstance(payload["inferences"], dict):
        errors.append("type:inferences")
    if "suggested_actions" in payload and not isinstance(payload["suggested_actions"], list):
        errors.append("type:suggested_actions")
    _validate_uncertain_fields(payload.get("uncertain_fields"), errors)
    _validate_teaching_judgment(payload.get("teaching_judgment"), errors)
    return errors


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


def _validate_teaching_judgment(value: object, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("type:teaching_judgment")
        return
    extra = set(value) - {"diagnosis", "evidence_basis", "risk"}
    errors.extend(f"extra:teaching_judgment.{field}" for field in sorted(extra))
    for field in ("diagnosis", "evidence_basis", "risk"):
        if field not in value:
            errors.append(f"missing:teaching_judgment.{field}")
    for field in ("diagnosis", "risk"):
        if field in value and not isinstance(value[field], str):
            errors.append(f"type:teaching_judgment.{field}")
    if "evidence_basis" in value and not isinstance(value["evidence_basis"], list):
        errors.append("type:teaching_judgment.evidence_basis")
    if isinstance(value.get("evidence_basis"), list):
        for index, item in enumerate(value["evidence_basis"]):
            if not isinstance(item, str):
                errors.append(f"type:teaching_judgment.evidence_basis[{index}]")


def _fake_provider_output(
    record: EvidenceRecord,
    asset_ids: list[str],
    provider_mode: ProviderMode,
) -> dict[str, Any]:
    if provider_mode == "invalid_schema":
        return {"confirmed_facts": {"asset_count": len(asset_ids)}}
    return {
        "confirmed_facts": {
            "record_id": record.id,
            "asset_count": len(asset_ids),
            "study_date": record.study_date.isoformat(),
        },
        "inferences": {"provider": FAKE_PROVIDER, "ocr_performed": False},
        "uncertain_fields": [
            {
                "field": "ocr_text",
                "reason": "fake provider does not read image content",
                "confidence": 0.2,
            }
        ],
        "teaching_judgment": {
            "diagnosis": "pending_user_confirmation",
            "evidence_basis": [f"asset:{asset_id}" for asset_id in asset_ids],
            "risk": "needs_human_review",
        },
        "suggested_actions": [{"type": "confirm_or_edit", "priority": "normal"}],
    }


def _asset_ids_for_record(session: Session, record_id: str) -> list[str]:
    return list(
        session.scalars(
            select(EvidenceAsset.asset_id)
            .where(EvidenceAsset.evidence_record_id == record_id)
            .order_by(EvidenceAsset.page_order)
        ).all()
    )


def _write_upload_to_cache(settings: RuntimeSettings, file: EvidenceFileInput) -> Path:
    try:
        data = base64.b64decode(file.content_base64, validate=True)
    except ValueError as exc:
        raise EvidenceError(
            "evidence file content_base64 is invalid",
            code="EVIDENCE_FILE_BASE64_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            details={"original_name": file.original_name},
        ) from exc
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    path = settings.cache_dir / f"evidence-upload-{uuid4().hex}-{file.original_name}"
    if Path(file.original_name).name != file.original_name:
        raise EvidenceError(
            "evidence original_name must be a file name",
            code="EVIDENCE_FILE_NAME_INVALID",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    path.write_bytes(data)
    return path
