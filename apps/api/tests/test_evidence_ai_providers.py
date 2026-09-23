import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.evidence.providers import (
    EvidenceAnalysisInput,
    EvidenceImage,
    EvidenceProviderError,
    OpenAICompatibleEvidenceProvider,
)
from app.settings import (
    EvidenceAIProviderName,
    EvidenceAISettings,
    get_settings,
)

FAKE_PROVIDER_TOKEN = "-".join(("test", "provider", "credential"))


def test_deepseek_provider_sends_images_and_parses_structured_json() -> None:
    captured: dict[str, Any] = {}
    expected = _valid_output()

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(expected)}}]},
        )

    settings = EvidenceAISettings(
        provider=EvidenceAIProviderName.DEEPSEEK,
        base_url="https://api.deepseek.com",
        api_key=FAKE_PROVIDER_TOKEN,
        model="deepseek-flash",
        timeout_seconds=60,
    )
    provider = OpenAICompatibleEvidenceProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )
    result = provider.analyze(
        EvidenceAnalysisInput(
            record_id="record-1",
            study_date="2026-09-23",
            asset_ids=["asset-1"],
            images=[
                EvidenceImage(
                    asset_id="asset-1",
                    mime_type="image/png",
                    content_base64="cG5n",
                )
            ],
        )
    )

    assert result == expected
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["authorization"] == f"Bearer {FAKE_PROVIDER_TOKEN}"
    payload = captured["payload"]
    assert payload["model"] == "deepseek-flash"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"][0]["content"][1] == {
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,cG5n", "detail": "original"},
    }


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [(401, "AI_PROVIDER_AUTH_FAILED"), (429, "AI_PROVIDER_RATE_LIMITED")],
)
def test_provider_returns_sanitized_upstream_errors(
    status_code: int,
    expected_code: str,
) -> None:
    secret_response = "upstream-secret-body"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=secret_response)

    provider = OpenAICompatibleEvidenceProvider(
        EvidenceAISettings(
            provider=EvidenceAIProviderName.OPENAI_COMPATIBLE,
            base_url="https://example-provider.invalid/v1",
            api_key=FAKE_PROVIDER_TOKEN,
            model="vision-model",
            timeout_seconds=60,
        ),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EvidenceProviderError) as captured:
        provider.analyze(_analysis_input())

    assert captured.value.code == expected_code
    assert secret_response not in str(captured.value)
    assert FAKE_PROVIDER_TOKEN not in str(captured.value)


def test_deepseek_settings_use_official_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    monkeypatch.setenv("YANTU_EVIDENCE_AI_PROVIDER", "deepseek")
    monkeypatch.setenv("YANTU_EVIDENCE_AI_API_KEY", "server-side-secret")
    get_settings.cache_clear()

    settings = get_settings().evidence_ai

    assert settings.provider is EvidenceAIProviderName.DEEPSEEK
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.model == "deepseek-flash"
    assert "server-side-secret" not in repr(settings)
    get_settings.cache_clear()


def test_openai_compatible_settings_require_explicit_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANTU_APP_ENV", "test")
    monkeypatch.setenv("YANTU_DATA_ROOT", str(tmp_path / "data" / "test"))
    monkeypatch.setenv("YANTU_EVIDENCE_AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("YANTU_EVIDENCE_AI_API_KEY", "server-side-secret")
    monkeypatch.delenv("YANTU_EVIDENCE_AI_BASE_URL", raising=False)
    monkeypatch.delenv("YANTU_EVIDENCE_AI_MODEL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="YANTU_EVIDENCE_AI_BASE_URL"):
        get_settings()
    get_settings.cache_clear()


def _analysis_input() -> EvidenceAnalysisInput:
    return EvidenceAnalysisInput(
        record_id="record-1",
        study_date="2026-09-23",
        asset_ids=["asset-1"],
        images=[EvidenceImage("asset-1", "image/png", "cG5n")],
    )


def _valid_output() -> dict[str, Any]:
    return {
        "confirmed_facts": {"visible_text": "example"},
        "inferences": {"topic": "math"},
        "uncertain_fields": [],
        "teaching_judgment": {
            "diagnosis": "needs review",
            "evidence_basis": ["asset:asset-1"],
            "risk": "model output requires confirmation",
        },
        "suggested_actions": [{"type": "confirm_or_edit"}],
    }
