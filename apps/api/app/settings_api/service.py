import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.schemas.settings import ProfileResponse, ProfileUpdate, RuleFileResponse, RulesResponse
from app.settings import RuntimeSettings

DEFAULT_PROFILE: dict[str, Any] = {
    "name": "考研学习者",
    "target_school": "大连理工大学",
    "target_major": "控制科学与工程学硕",
    "exam_date": None,
    "current_phase": "foundation",
    "coach_style": "direct",
    "timezone": "Asia/Shanghai",
}

RULE_FILES = {
    "mastery": "config/mastery_rules.v1.yaml",
    "planning": "config/planning_rules.v1.yaml",
    "quality_gates": "config/quality_gates.yml",
}


class SettingsApiError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int,
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def read_profile(settings: RuntimeSettings) -> ProfileResponse:
    payload = _load_profile_payload(settings)
    return _profile_response(payload)


def update_profile(settings: RuntimeSettings, update: ProfileUpdate) -> ProfileResponse:
    payload = _load_profile_payload(settings)
    updates = update.model_dump(exclude_unset=True)
    for key, value in updates.items():
        payload[key] = (
            value.isoformat() if hasattr(value, "isoformat") and value is not None else value
        )
    payload["updated_at"] = datetime.now(UTC).isoformat()
    _profile_path(settings).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return _profile_response(payload)


def read_rules() -> RulesResponse:
    repo_root = _repo_root()
    items = []
    for key, relative in RULE_FILES.items():
        path = repo_root / relative
        if not path.is_file():
            raise SettingsApiError(
                "rule file not found",
                code="RULE_FILE_NOT_FOUND",
                status_code=404,
                details={"path": relative},
            )
        content = path.read_text(encoding="utf-8")
        items.append(
            RuleFileResponse(
                key=key,
                version=_extract_version(content),
                path=relative.replace("\\", "/"),
                sha256=sha256(content.encode("utf-8")).hexdigest(),
                content=content,
            )
        )
    return RulesResponse(items=items, total=len(items))


def _load_profile_payload(settings: RuntimeSettings) -> dict[str, Any]:
    path = _profile_path(settings)
    if not path.is_file():
        payload = {**DEFAULT_PROFILE, "updated_at": datetime.now(UTC).isoformat()}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return payload
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsApiError(
            "profile settings file is not valid JSON",
            code="PROFILE_SETTINGS_INVALID",
            status_code=422,
        ) from exc
    if not isinstance(payload, dict):
        raise SettingsApiError(
            "profile settings payload must be an object",
            code="PROFILE_SETTINGS_INVALID",
            status_code=422,
        )
    return {**DEFAULT_PROFILE, **payload}


def _profile_response(payload: dict[str, Any]) -> ProfileResponse:
    return ProfileResponse.model_validate(payload)


def _profile_path(settings: RuntimeSettings) -> Path:
    settings.settings_dir.mkdir(parents=True, exist_ok=True)
    return settings.settings_dir / "profile.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _extract_version(content: str) -> str | None:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("version:"):
            return stripped.split(":", 1)[1].strip().strip("\"'")
    return None
