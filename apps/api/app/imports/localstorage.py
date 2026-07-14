import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_batch import ImportBatch
from app.services.audit import write_audit_event

LOCAL_STORAGE_KEY = "postgradCoachV11"
MAX_IMPORT_BYTES = 1024 * 1024

KNOWN_TOP_LEVEL_FIELDS = {
    "version",
    "settings",
    "today",
    "tasks",
    "knowledge",
    "wrongs",
    "resources",
    "inbox",
    "goals",
    "records",
    "adjustments",
}

FIELD_MAPPINGS = {
    "settings": "profile",
    "today": "daily_context",
    "tasks": "tasks",
    "knowledge": "mastery_imports",
    "wrongs": "wrong_items",
    "resources": "resources",
    "inbox": "inbox",
    "goals": "goals",
    "records": "records",
    "adjustments": "plan_adjustments",
}

OBJECT_FIELDS = {"settings", "today"}
LIST_FIELDS = {
    "tasks",
    "knowledge",
    "wrongs",
    "resources",
    "inbox",
    "goals",
    "records",
    "adjustments",
}

KNOWN_CHILD_FIELDS = {
    "settings": {
        "school",
        "major",
        "subjects",
        "phase",
        "examDate",
        "defaultMinutes",
        "peakTime",
        "coachStyle",
    },
    "today": {"availableMinutes", "energy", "subject"},
    "tasks": {
        "id",
        "subject",
        "title",
        "minutes",
        "priority",
        "source",
        "reason",
        "standard",
        "from",
        "to",
        "knowledge",
        "status",
    },
    "knowledge": {
        "id",
        "subject",
        "path",
        "name",
        "stage",
        "recall",
        "basic",
        "variant",
        "transfer",
        "errors",
        "next",
    },
    "wrongs": {
        "id",
        "subject",
        "knowledge",
        "type",
        "cause",
        "deep",
        "errors",
        "redos",
        "next",
        "status",
    },
    "resources": {"name", "subject", "status", "unit"},
    "inbox": {"id", "name", "type", "status"},
    "goals": {"level", "name", "parent", "progress", "risk"},
    "records": {"id", "date", "task", "knowledge", "evidence", "minutes", "status"},
    "adjustments": {"date", "title", "text"},
}


class LocalStorageImportError(ValueError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.details = details
        super().__init__(message)


@dataclass(frozen=True)
class LocalStoragePreview:
    source_key: str
    source_sha256: str
    source_version: str
    size_bytes: int
    raw_payload: dict[str, Any]
    recognized_fields: list[str]
    unknown_fields: list[str]
    entity_counts: dict[str, int]
    mastery_status: Literal["none", "imported_unverified"]
    summary: dict[str, Any]
    report: dict[str, Any]


@dataclass(frozen=True)
class LocalStorageCommitResult:
    preview: LocalStoragePreview
    batch_id: str
    created: bool
    status: Literal["committed"]


@dataclass(frozen=True)
class _NormalizedPayload:
    source_key: str
    data: dict[str, Any]
    canonical_json: str
    source_sha256: str
    size_bytes: int


def build_localstorage_preview(raw_payload: Any) -> LocalStoragePreview:
    normalized = _normalize_payload(raw_payload)
    data = normalized.data
    recognized_fields = [field for field in data if field in KNOWN_TOP_LEVEL_FIELDS]
    unknown_fields = _find_unknown_fields(data)
    entity_counts = _count_entities(data)
    mastery_status: Literal["none", "imported_unverified"] = (
        "imported_unverified" if entity_counts.get("knowledge", 0) > 0 else "none"
    )
    summary = {
        "source_key": normalized.source_key,
        "source_sha256": normalized.source_sha256,
        "source_version": str(data["version"]),
        "size_bytes": normalized.size_bytes,
        "recognized_fields": recognized_fields,
        "unknown_fields": unknown_fields,
        "entity_counts": entity_counts,
        "mastery_status": mastery_status,
    }
    report = _build_report(summary)
    return LocalStoragePreview(
        source_key=normalized.source_key,
        source_sha256=normalized.source_sha256,
        source_version=str(data["version"]),
        size_bytes=normalized.size_bytes,
        raw_payload=data,
        recognized_fields=recognized_fields,
        unknown_fields=unknown_fields,
        entity_counts=entity_counts,
        mastery_status=mastery_status,
        summary=summary,
        report=report,
    )


def commit_localstorage_import(
    session: Session,
    raw_payload: Any,
    *,
    request_id: str | None = None,
) -> LocalStorageCommitResult:
    preview = build_localstorage_preview(raw_payload)
    existing = session.scalar(
        select(ImportBatch).where(
            ImportBatch.source_key == preview.source_key,
            ImportBatch.source_sha256 == preview.source_sha256,
        )
    )
    if existing is not None:
        return LocalStorageCommitResult(
            preview=preview,
            batch_id=existing.id,
            created=False,
            status="committed",
        )

    batch = ImportBatch(
        id=str(uuid4()),
        source_key=preview.source_key,
        source_sha256=preview.source_sha256,
        source_version=preview.source_version,
        status="committed",
        size_bytes=preview.size_bytes,
        raw_payload_json=preview.raw_payload,
        summary_json=preview.summary,
        report_json=preview.report,
        request_id=request_id,
    )
    session.add(batch)
    session.flush()
    write_audit_event(
        session,
        event_type="localstorage_import.committed",
        actor_type="system",
        object_type="import_batch",
        object_id=batch.id,
        after_json=preview.summary,
        reason="localStorage prototype import committed",
        request_id=request_id,
    )
    return LocalStorageCommitResult(
        preview=preview,
        batch_id=batch.id,
        created=True,
        status="committed",
    )


def _normalize_payload(raw_payload: Any) -> _NormalizedPayload:
    source_key, data = _unwrap_payload(raw_payload)
    _validate_source_key(source_key)
    _validate_data_shape(data)
    canonical_json = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    size_bytes = len(canonical_json.encode("utf-8"))
    if size_bytes > MAX_IMPORT_BYTES:
        raise LocalStorageImportError(
            "localStorage import payload is too large",
            details={"max_bytes": MAX_IMPORT_BYTES, "actual_bytes": size_bytes},
        )
    return _NormalizedPayload(
        source_key=source_key,
        data=data,
        canonical_json=canonical_json,
        source_sha256=hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
        size_bytes=size_bytes,
    )


def _unwrap_payload(raw_payload: Any) -> tuple[str, dict[str, Any]]:
    payload = _decode_json_if_needed(raw_payload, path="$")
    if not isinstance(payload, dict):
        raise LocalStorageImportError(
            "localStorage import payload must be a JSON object",
            details={"path": "$"},
        )

    source_key = LOCAL_STORAGE_KEY
    source_value: Any = payload
    if "source_key" in payload and "payload" in payload:
        source_key = _coerce_source_key(payload["source_key"])
        source_value = payload["payload"]
    elif "key" in payload and "value" in payload:
        source_key = _coerce_source_key(payload["key"])
        source_value = payload["value"]
    elif LOCAL_STORAGE_KEY in payload:
        source_value = payload[LOCAL_STORAGE_KEY]

    decoded_value = _decode_json_if_needed(source_value, path=source_key)
    if not isinstance(decoded_value, dict):
        raise LocalStorageImportError(
            "localStorage value must decode to a JSON object",
            details={"source_key": source_key},
        )
    return source_key, decoded_value


def _decode_json_if_needed(value: Any, *, path: str) -> Any:
    if isinstance(value, bytes | bytearray):
        try:
            value = bytes(value).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LocalStorageImportError(
                "localStorage import payload must be UTF-8 JSON",
                details={"path": path},
            ) from exc
    if isinstance(value, str):
        size_bytes = len(value.encode("utf-8"))
        if size_bytes > MAX_IMPORT_BYTES:
            raise LocalStorageImportError(
                "localStorage import payload is too large",
                details={"max_bytes": MAX_IMPORT_BYTES, "actual_bytes": size_bytes},
            )
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise LocalStorageImportError(
                "localStorage import payload is not valid JSON",
                details={"path": path, "position": exc.pos},
            ) from exc
    return value


def _coerce_source_key(value: Any) -> str:
    if not isinstance(value, str):
        raise LocalStorageImportError(
            "localStorage source key must be a string",
            details={"expected": LOCAL_STORAGE_KEY},
        )
    return value


def _validate_source_key(source_key: str) -> None:
    if source_key != LOCAL_STORAGE_KEY:
        raise LocalStorageImportError(
            "unsupported localStorage source key",
            details={"expected": LOCAL_STORAGE_KEY, "received": source_key},
        )


def _validate_data_shape(data: dict[str, Any]) -> None:
    if "version" not in data:
        raise LocalStorageImportError(
            "localStorage import payload is missing required field: version",
            details={"missing": ["version"]},
        )
    if not isinstance(data["version"], str | int | float):
        raise LocalStorageImportError(
            "localStorage version must be a scalar value",
            details={"field": "version"},
        )
    for field in OBJECT_FIELDS:
        if field in data and not isinstance(data[field], dict):
            raise LocalStorageImportError(
                f"localStorage field must be an object: {field}",
                details={"field": field},
            )
    for field in LIST_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if not isinstance(value, list):
            raise LocalStorageImportError(
                f"localStorage field must be a list: {field}",
                details={"field": field},
            )
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise LocalStorageImportError(
                    f"localStorage list item must be an object: {field}[{index}]",
                    details={"field": field, "index": index},
                )


def _find_unknown_fields(data: dict[str, Any]) -> list[str]:
    unknown_fields = sorted(field for field in data if field not in KNOWN_TOP_LEVEL_FIELDS)
    for field, allowed_children in KNOWN_CHILD_FIELDS.items():
        if field not in data:
            continue
        value = data[field]
        if isinstance(value, dict):
            unknown_fields.extend(
                f"{field}.{child}" for child in sorted(value) if child not in allowed_children
            )
            continue
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    unknown_fields.extend(
                        f"{field}[{index}].{child}"
                        for child in sorted(item)
                        if child not in allowed_children
                    )
    return unknown_fields


def _count_entities(data: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in FIELD_MAPPINGS:
        if field not in data:
            counts[field] = 0
            continue
        value = data[field]
        if isinstance(value, list):
            counts[field] = len(value)
        elif isinstance(value, dict):
            counts[field] = 1
        else:
            counts[field] = 0
    return counts


def _build_report(summary: dict[str, Any]) -> dict[str, Any]:
    entity_counts = summary["entity_counts"]
    mapped_entities = {
        target: {"source_field": source, "count": entity_counts[source]}
        for source, target in FIELD_MAPPINGS.items()
    }
    return {
        "source": {
            "key": summary["source_key"],
            "sha256": summary["source_sha256"],
            "version": summary["source_version"],
            "size_bytes": summary["size_bytes"],
        },
        "mapped_entities": mapped_entities,
        "unknown_fields": summary["unknown_fields"],
        "mastery": {
            "source_field": "knowledge",
            "count": entity_counts["knowledge"],
            "verification": summary["mastery_status"],
            "reason": "historical mastery data has no attached evidence in the prototype export",
        },
        "warnings": _build_warnings(summary),
    }


def _build_warnings(summary: dict[str, Any]) -> list[str]:
    warnings = []
    if summary["unknown_fields"]:
        warnings.append("unknown_fields_preserved")
    if summary["mastery_status"] == "imported_unverified":
        warnings.append("mastery_marked_imported_unverified")
    return warnings
