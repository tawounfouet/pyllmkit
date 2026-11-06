"""S4: strict native generation parameters across all six provider codecs.

Each test uses a real pure native request encoder and an explicitly
constructed PreparedInvocation, never an external provider API.
Adversarial cases bypass the service on purpose: adapters must not
silently accept a forged or stale non-NATIVE capability assessment.
"""

import json
from dataclasses import replace

import pytest

from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    encode_anthropic_messages_request,
)
from pyllmkit.adapters.inference.google_gemini_mapping import encode_gemini_request
from pyllmkit.adapters.inference.mistral_chat_mapping import encode_mistral_chat_request
from pyllmkit.adapters.inference.ollama_mapping import encode_ollama_request
from pyllmkit.adapters.inference.openai_responses_mapping import (
    encode_openai_responses_request,
)
from pyllmkit.adapters.inference.xai_responses_mapping import (
    encode_xai_responses_request,
)
from pyllmkit.application.inference import (
    InvocationPortError,
    InvocationPreconditionError,
    PreparedInvocation,
)
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.inference import (
    GENERATION_PARAMETER_NAMES,
    CompatibilityReport,
    GenerationConfig,
    GenerationSupportSnapshot,
    ParameterAssessment,
    ParameterSupport,
)
from tests.conformance.providers import PROVIDERS, prepared
from tests.conformance.test_v030_s1_native_text_profile import _fixture

_ENCODERS = {
    "openai": encode_openai_responses_request,
    "anthropic": encode_anthropic_messages_request,
    "google": encode_gemini_request,
    "xai": encode_xai_responses_request,
    "mistral": encode_mistral_chat_request,
    "ollama": encode_ollama_request,
}

_NATIVE_NAMES: dict[str, dict[str, str]] = {
    "openai": {
        "temperature": "temperature", "top_p": "top_p",
        "max_output_tokens": "max_output_tokens",
    },
    "anthropic": {
        "temperature": "temperature", "top_p": "top_p", "top_k": "top_k",
        "max_output_tokens": "max_tokens", "stop_sequences": "stop_sequences",
    },
    "google": {
        "temperature": "temperature", "top_p": "topP", "top_k": "topK",
        "max_output_tokens": "maxOutputTokens", "seed": "seed",
        "stop_sequences": "stopSequences", "presence_penalty": "presencePenalty",
        "frequency_penalty": "frequencyPenalty",
    },
    "xai": {
        "temperature": "temperature", "top_p": "top_p",
        "max_output_tokens": "max_output_tokens",
    },
    "mistral": {
        "temperature": "temperature", "top_p": "top_p", "top_k": "top_k",
        "max_output_tokens": "max_tokens", "seed": "random_seed",
        "stop_sequences": "stop", "presence_penalty": "presence_penalty",
        "frequency_penalty": "frequency_penalty",
    },
    "ollama": {
        "temperature": "temperature", "top_p": "top_p", "top_k": "top_k",
        "max_output_tokens": "num_predict", "seed": "seed",
        "stop_sequences": "stop",
    },
}

_VALUES: dict[str, object] = {
    "temperature": 0.25,
    "top_p": 0.85,
    "top_k": 4,
    "max_output_tokens": 128,
    "seed": 17,
    "stop_sequences": ("END",),
    "presence_penalty": 0.4,
    "frequency_penalty": -0.2,
}
_CORE_PARAMETERS = ("temperature", "top_p", "max_output_tokens")
_NON_NATIVE_LEVELS = (
    None, SupportLevel.UNSUPPORTED, SupportLevel.PARTIAL, SupportLevel.EMULATED,
)


def _case(
    provider: str, name: str, level: SupportLevel | None,
    *, include_declaration: bool = True,
) -> PreparedInvocation:
    base = prepared(provider)
    fields = {"max_output_tokens": 128, name: _VALUES[name]}
    request = replace(base.request, generation_config=GenerationConfig(**fields))
    assessment = []
    if name != "max_output_tokens":
        assessment.append(ParameterAssessment("max_output_tokens", SupportLevel.NATIVE))
    if include_declaration:
        assessment.append(ParameterAssessment(name, level))
    return replace(
        base,
        request=request,
        parameter_assessment=CompatibilityReport(tuple(assessment)),
    )


def _generation(provider: str, payload: dict[str, object]) -> dict[str, object]:
    if provider == "google":
        obj = payload["generationConfig"]
    elif provider == "ollama":
        obj = payload["options"]
    else:
        obj = payload
    assert isinstance(obj, dict)
    return obj


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("name", GENERATION_PARAMETER_NAMES)
def test_explicit_native_parameter_is_mapped_or_rejected(
    provider: str, name: str,
) -> None:
    case = _case(provider, name, SupportLevel.NATIVE)
    native_name = _NATIVE_NAMES[provider].get(name)
    if native_name is None:
        with pytest.raises(
            InvocationPortError, match="unsupported_generation_parameter",
        ):
            _ENCODERS[provider](case)
        return

    raw = _ENCODERS[provider](case)
    body = json.loads(raw)
    assert isinstance(body, dict)
    generation = _generation(provider, body)
    expected = list(_VALUES[name]) if name == "stop_sequences" else _VALUES[name]
    assert generation[native_name] == expected
    assert list(generation).count(native_name) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("name", _CORE_PARAMETERS)
@pytest.mark.parametrize(
    "level", _NON_NATIVE_LEVELS, ids=("unknown", "unsupported", "partial", "emulated"),
)
def test_adapter_rejects_non_native_assessment_even_when_prepared(
    provider: str, name: str, level: SupportLevel | None,
) -> None:
    case = _case(provider, name, level)
    with pytest.raises(InvocationPortError, match="unknown_generation_parameter"):
        _ENCODERS[provider](case)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("name", _CORE_PARAMETERS)
def test_adapter_rejects_missing_assessment_without_silent_acceptance(
    provider: str, name: str,
) -> None:
    case = _case(provider, name, None, include_declaration=False)
    with pytest.raises(InvocationPortError, match="unknown_generation_parameter"):
        _ENCODERS[provider](case)


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize(
    "level", _NON_NATIVE_LEVELS, ids=("unknown", "unsupported", "partial", "emulated"),
)
def test_application_refuses_non_native_support_before_adapter(
    provider: str, level: SupportLevel | None,
) -> None:
    _case_unused, service, request, fake = _fixture(provider, include_snapshot=False)
    descriptor = CapabilitySupport(
        level, notes="restrictions apply" if level is SupportLevel.PARTIAL else None,
    )
    snapshot = GenerationSupportSnapshot(
        request.target, (ParameterSupport("max_output_tokens", descriptor),),
    )
    expected = (
        "unsupported_generation_parameter"
        if level is SupportLevel.UNSUPPORTED else "unknown_generation_parameter"
    )
    with pytest.raises(InvocationPreconditionError, match=expected):
        service.invoke(request, snapshot)
    assert fake.calls == []
