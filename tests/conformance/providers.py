"""Hermetic test factories for real P7 native adapters, never live provider traffic.

Only the in-memory fake is used to prepare a valid immutable invocation;
the target of conformance tests is the *real* vendor HTTP adapter using
an injected httpx.MockTransport. No credentials from process environment.
"""

from __future__ import annotations

from typing import Any

import httpx

from pyllmkit.adapters.inference import (
    AnthropicMessagesAdapter,
    AsyncAnthropicMessagesAdapter,
    AsyncGoogleGeminiAdapter,
    AsyncMistralChatAdapter,
    AsyncOllamaAdapter,
    AsyncOpenAIResponsesAdapter,
    AsyncXAIResponsesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    GoogleGeminiAdapter,
    MistralChatAdapter,
    OllamaAdapter,
    OpenAIResponsesAdapter,
    ProviderConnectionConfig,
    XAIResponsesAdapter,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import InferenceService, PreparedInvocation
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    ParameterSupport,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId

PROVIDERS = ("openai", "anthropic", "google", "xai", "mistral", "ollama")
FAKE_SECRET = "PYLLMKIT-V030-SYNTHETIC-SECRET-NOT-A-REAL-KEY"
_MOCK_ENV_NAME = "PYLLMKIT_V030_SYNTHETIC_KEY"
_ALIAS = "synthetic-text-model"

_SYNC: dict[str, type] = {
    "openai": OpenAIResponsesAdapter,
    "anthropic": AnthropicMessagesAdapter,
    "google": GoogleGeminiAdapter,
    "xai": XAIResponsesAdapter,
    "mistral": MistralChatAdapter,
    "ollama": OllamaAdapter,
}
_ASYNC: dict[str, type] = {
    "openai": AsyncOpenAIResponsesAdapter,
    "anthropic": AsyncAnthropicMessagesAdapter,
    "google": AsyncGoogleGeminiAdapter,
    "xai": AsyncXAIResponsesAdapter,
    "mistral": AsyncMistralChatAdapter,
    "ollama": AsyncOllamaAdapter,
}


def prepared(provider: str) -> PreparedInvocation:
    """A matching deployment, target and NATIVE max_output_tokens support."""
    if provider not in PROVIDERS:
        raise ValueError("unsupported_test_provider")
    catalog = InMemoryCatalog()
    modes = frozenset({Modality("text")})
    modalities = ModalitySet(modes, modes)
    model_id = ModelId(f"v030-model-{provider}")
    provider_id = None if provider == "ollama" else ProviderId(provider)
    dep_id = DeploymentId(f"v030-deployment-{provider}")
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
            runtime="ollama" if provider == "ollama" else "cloud",
            modalities=modalities,
        )
    )
    request = InferenceRequest(
        DeploymentTarget(dep_id),
        (Message(Role.USER, Content((TextContent("synthetic user input"),))),),
        GenerationConfig(max_output_tokens=128),
    )
    snapshot = GenerationSupportSnapshot(
        request.target,
        (ParameterSupport(
            "max_output_tokens", CapabilitySupport(SupportLevel.NATIVE),
        ),),
    )
    fake = FakeInferenceAdapter()
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        fake, {dep_id: _ALIAS},
    )
    result = service.invoke(request, snapshot)
    assert result.response is not None
    assert len(fake.calls) == 1
    return fake.calls[0]


def adapter(
    provider: str,
    *,
    transport: httpx.MockTransport,
    async_mode: bool,
    allow_live: bool = True,
) -> Any:
    """Use an injected local MockTransport, never a real socket.

    allow_live means the adapter's explicit opt-in gate is set. It does not
    authorize or initiate any real network traffic in this test factory.
    """
    if provider not in PROVIDERS:
        raise ValueError("unsupported_test_provider")
    cls = (_ASYNC if async_mode else _SYNC)[provider]
    if provider == "ollama":
        return cls(
            ProviderConnectionConfig.ollama_local(),
            allow_live=allow_live,
            _test_transport=transport,
        )
    ref = CredentialRef(f"v030-{provider}-synthetic")
    configs = {
        "openai": ProviderConnectionConfig.openai,
        "anthropic": ProviderConnectionConfig.anthropic,
        "google": ProviderConnectionConfig.google,
        "xai": ProviderConnectionConfig.xai,
        "mistral": ProviderConnectionConfig.mistral,
    }
    config = configs[provider](ref)
    resolver = EnvCredentialResolver(
        {ref: _MOCK_ENV_NAME},
        environ={_MOCK_ENV_NAME: FAKE_SECRET},
    )
    return cls(
        config, resolver, allow_live=allow_live, _test_transport=transport,
    )
