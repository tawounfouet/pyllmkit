"""S1 cross-provider text contract fixtures, no HTTP clients or network.

This is an initial executable profile for pure native encoders. S2 will add
actual provider adapter MockTransport and sync/async response conformance.
"""

import json
from collections.abc import Callable

import pytest

from pyllmkit.adapters.inference import FakeInferenceAdapter
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
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    InferenceService,
    InvocationPortError,
    InvocationPreconditionError,
    PreparedInvocation,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    InferenceRunState,
    ParameterSupport,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId

_ENCODERS: dict[str, Callable[[PreparedInvocation], bytes]] = {
    "openai": encode_openai_responses_request,
    "anthropic": encode_anthropic_messages_request,
    "google": encode_gemini_request,
    "xai": encode_xai_responses_request,
    "mistral": encode_mistral_chat_request,
    "ollama": encode_ollama_request,
}

_PROVIDER_MODEL_ALIAS = "synthetic-text-model"
_USER_TEXT = "Bonjour, monde! Élève ☀"


def _messages(*roles: Role) -> tuple[Message, ...]:
    return tuple(
        Message(role, Content((TextContent(_USER_TEXT),)))
        for role in roles
    )


def _fixture(
    provider: str, roles: tuple[Role, ...] = (Role.USER,),
    *, include_snapshot: bool = True,
) -> tuple[PreparedInvocation | None, InferenceService, InferenceRequest, FakeInferenceAdapter]:
    catalog = InMemoryCatalog()
    text = frozenset({Modality("text")})
    modalities = ModalitySet(text, text)
    model_id = ModelId(f"model-{provider}")
    dep_id = DeploymentId(f"deployment-{provider}")
    provider_id = None if provider == "ollama" else ProviderId(provider)
    runtime = "ollama" if provider == "ollama" else "cloud"
    catalog.models.register(
        Model(model_id, ModelIdentity(ModelFamily("synthetic")), modalities=modalities)
    )
    if provider_id is not None:
        catalog.providers.register(
            InferenceProvider(provider_id, provider, modalities=modalities)
        )
    catalog.deployments.register(
        Deployment(
            dep_id, model_id, provider_id, DeploymentStatus.AVAILABLE,
            runtime=runtime, modalities=modalities,
        )
    )
    request = InferenceRequest(
        DeploymentTarget(dep_id), _messages(*roles),
        GenerationConfig(max_output_tokens=128),
    )
    adapter = FakeInferenceAdapter()
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        adapter,
        {dep_id: _PROVIDER_MODEL_ALIAS},
    )
    if not include_snapshot:
        return None, service, request, adapter
    snapshot = GenerationSupportSnapshot(
        request.target,
        (ParameterSupport(
            "max_output_tokens", CapabilitySupport(SupportLevel.NATIVE),
        ),),
    )
    outcome = service.invoke(request, snapshot)
    assert outcome.run.state is InferenceRunState.COMPLETED
    assert len(adapter.calls) == 1
    return adapter.calls[0], service, request, adapter


def _native_messages(provider: str, body: dict[str, object]) -> list[object]:
    if provider in {"openai", "xai"}:
        value = body["input"]
    elif provider == "google":
        value = body["contents"]
    else:
        value = body["messages"]
    assert isinstance(value, list)
    return value


@pytest.mark.parametrize("provider", sorted(_ENCODERS))
def test_six_native_encoders_preserve_text_and_explicit_token_limit(provider: str) -> None:
    prepared, _, _, _ = _fixture(provider)
    assert prepared is not None

    raw = _ENCODERS[provider](prepared)
    assert type(raw) is bytes
    assert raw == _ENCODERS[provider](prepared)
    body = json.loads(raw)
    assert isinstance(body, dict)

    messages = _native_messages(provider, body)
    assert len(messages) == 1
    item = messages[0]
    assert isinstance(item, dict)
    assert item["role"] == "user"
    if provider in {"openai", "xai", "mistral", "ollama"}:
        assert item["content"] == _USER_TEXT
    elif provider == "anthropic":
        assert item["content"] == [{"type": "text", "text": _USER_TEXT}]
    else:
        assert item["parts"] == [{"text": _USER_TEXT}]

    if provider in {"openai", "xai"}:
        assert body["max_output_tokens"] == 128
    elif provider in {"anthropic", "mistral"}:
        assert body["max_tokens"] == 128
    elif provider == "google":
        generation = body["generationConfig"]
        assert isinstance(generation, dict)
        assert generation["maxOutputTokens"] == 128
    else:
        options = body["options"]
        assert isinstance(options, dict)
        assert options["num_predict"] == 128


@pytest.mark.parametrize("provider", sorted(_ENCODERS))
def test_generation_snapshot_missing_fails_before_adapter(provider: str) -> None:
    _, service, request, adapter = _fixture(provider, include_snapshot=False)
    with pytest.raises(
        InvocationPreconditionError, match="generation_support_snapshot_missing",
    ):
        service.invoke(request)
    assert adapter.calls == []


@pytest.mark.parametrize("provider", sorted(_ENCODERS))
def test_developer_role_is_not_silently_coerced(provider: str) -> None:
    prepared, _, _, _ = _fixture(provider, (Role.DEVELOPER, Role.USER))
    assert prepared is not None
    if provider in {"openai", "xai"}:
        body = json.loads(_ENCODERS[provider](prepared))
        messages = _native_messages(provider, body)
        assert len(messages) == 2
        assert messages[0]["role"] == "developer"
        assert messages[1]["role"] == "user"
    else:
        with pytest.raises(InvocationPortError, match="unsupported_message_role"):
            _ENCODERS[provider](prepared)
