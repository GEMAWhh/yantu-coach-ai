import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

import httpx

from app.settings import EvidenceAIProviderName, EvidenceAISettings

ProviderMode = Literal["valid", "invalid_schema"]
PROMPT_VERSION = "evidence-draft-v1"


class EvidenceProviderError(RuntimeError):
    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class EvidenceImage:
    asset_id: str
    mime_type: str
    content_base64: str


@dataclass(frozen=True)
class EvidenceAnalysisInput:
    record_id: str
    study_date: str
    asset_ids: list[str]
    images: list[EvidenceImage]
    provider_mode: ProviderMode = "valid"


class EvidenceProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    @property
    def prompt_version(self) -> str: ...

    def analyze(self, analysis_input: EvidenceAnalysisInput) -> dict[str, Any]: ...


class FakeEvidenceProvider:
    provider_name = "fake"
    model_name = "fake-evidence-provider"
    prompt_version = "evidence-draft-fake-v1"

    def analyze(self, analysis_input: EvidenceAnalysisInput) -> dict[str, Any]:
        if analysis_input.provider_mode == "invalid_schema":
            return {"confirmed_facts": {"asset_count": len(analysis_input.asset_ids)}}
        return {
            "confirmed_facts": {
                "record_id": analysis_input.record_id,
                "asset_count": len(analysis_input.asset_ids),
                "study_date": analysis_input.study_date,
            },
            "inferences": {"provider": self.provider_name, "ocr_performed": False},
            "uncertain_fields": [
                {
                    "field": "ocr_text",
                    "reason": "fake provider does not read image content",
                    "confidence": 0.2,
                }
            ],
            "teaching_judgment": {
                "diagnosis": "pending_user_confirmation",
                "evidence_basis": [f"asset:{asset_id}" for asset_id in analysis_input.asset_ids],
                "risk": "needs_human_review",
            },
            "suggested_actions": [{"type": "confirm_or_edit", "priority": "normal"}],
        }


class OpenAICompatibleEvidenceProvider:
    prompt_version = PROMPT_VERSION

    def __init__(
        self,
        settings: EvidenceAISettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if settings.base_url is None or settings.api_key is None:
            raise ValueError("real AI provider settings are incomplete")
        self._settings = settings
        self._transport = transport

    @property
    def provider_name(self) -> str:
        return self._settings.provider.value

    @property
    def model_name(self) -> str:
        return self._settings.model

    def analyze(self, analysis_input: EvidenceAnalysisInput) -> dict[str, Any]:
        if analysis_input.provider_mode != "valid":
            raise EvidenceProviderError(
                code="AI_PROVIDER_MODE_INVALID",
                message="test provider modes are only available with the fake provider",
            )
        if not analysis_input.images:
            raise EvidenceProviderError(
                code="AI_IMAGE_REQUIRED",
                message="real evidence analysis requires at least one supported image",
            )

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": _analysis_prompt(analysis_input),
            }
        ]
        content.extend(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime_type};base64,{image.content_base64}",
                    "detail": "original",
                },
            }
            for image in analysis_input.images
        )
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        try:
            with httpx.Client(
                timeout=self._settings.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    f"{self._settings.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise EvidenceProviderError(
                code="AI_PROVIDER_TIMEOUT",
                message="AI provider request timed out",
            ) from exc
        except httpx.HTTPError as exc:
            raise EvidenceProviderError(
                code="AI_PROVIDER_UNAVAILABLE",
                message="AI provider is temporarily unavailable",
            ) from exc

        if response.status_code in {401, 403}:
            raise EvidenceProviderError(
                code="AI_PROVIDER_AUTH_FAILED",
                message="AI provider authentication failed",
            )
        if response.status_code == 429:
            raise EvidenceProviderError(
                code="AI_PROVIDER_RATE_LIMITED",
                message="AI provider rate limit was reached",
            )
        if not response.is_success:
            raise EvidenceProviderError(
                code="AI_PROVIDER_UNAVAILABLE",
                message="AI provider request failed",
            )

        try:
            envelope = response.json()
            content_value = envelope["choices"][0]["message"]["content"]
            if not isinstance(content_value, str):
                raise TypeError
            parsed = json.loads(_strip_json_fence(content_value))
            if not isinstance(parsed, dict):
                raise TypeError
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise EvidenceProviderError(
                code="AI_PROVIDER_RESPONSE_INVALID",
                message="AI provider returned an invalid response",
            ) from exc
        return cast(dict[str, Any], parsed)


def build_evidence_provider(settings: EvidenceAISettings) -> EvidenceProvider:
    if settings.provider is EvidenceAIProviderName.FAKE:
        return FakeEvidenceProvider()
    return OpenAICompatibleEvidenceProvider(settings)


def _analysis_prompt(analysis_input: EvidenceAnalysisInput) -> str:
    return f"""Analyze the attached study evidence images and return JSON only.
The JSON object must contain exactly these top-level fields:
- confirmed_facts: object containing only facts clearly visible in the images
- inferences: object containing interpretations that may be wrong
- uncertain_fields: array of objects with field, reason, confidence (0 to 1)
- teaching_judgment: object with diagnosis, evidence_basis (array of strings), risk
- suggested_actions: array of action objects

Never claim that a fact is confirmed when it is not visible. Do not issue SQL, file,
deployment, or deletion instructions. This result is an unconfirmed draft.
Record id: {analysis_input.record_id}
Study date: {analysis_input.study_date}
Asset ids: {json.dumps(analysis_input.asset_ids)}
"""


def _strip_json_fence(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("```json") and stripped.endswith("```"):
        return stripped[7:-3].strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return stripped[3:-3].strip()
    return stripped
