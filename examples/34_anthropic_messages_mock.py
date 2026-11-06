"""P7 L7.5 Anthropic Messages offline mock: zero cloud requests or real keys."""

import json

import httpx

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AnthropicMessagesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    ProviderConnectionConfig,
    RegisteredInferencePort,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import InferenceService
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


def main() -> None:
    catalog = InMemoryCatalog()
    modalities = ModalitySet(
        frozenset((Modality("text"),)), frozenset((Modality("text"),)),
    )
    model = ModelId("local-example-model")
    dep = DeploymentId("anthropic-demo")
    provider = ProviderId("anthropic")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("claude")), modalities=modalities,
    ))
    catalog.providers.register(InferenceProvider(
        provider, "Anthropic", modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        dep, model, provider, DeploymentStatus.AVAILABLE,
        runtime="cloud", modalities=modalities,
    ))

    def mock(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 32
        assert "tools" not in payload
        assert "thinking" not in payload
        assert request.headers["anthropic-version"] == "2026-10-21"
        return httpx.Response(
            200, json={
                "type": "message", "role": "assistant", "model": payload["model"],
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "synthetic-only"}],
                "usage": {"input_tokens": 2, "output_tokens": 2},
            }, headers={"content-type": "application/json"},
        )

    ref = CredentialRef("anthropic-demo")
    resolver = EnvCredentialResolver(
        {ref: "ANTHROPIC_API_KEY"}, environ={
            "ANTHROPIC_API_KEY": "not-real-and-not-for-cloud",
        },
    )
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(provider, "cloud"), ProviderConnectionConfig.anthropic(ref),
        sync_factory=lambda conn: AnthropicMessagesAdapter(
            conn, resolver, allow_live=True,
            _test_transport=httpx.MockTransport(mock),
        ),
    ))
    config = GenerationConfig(max_output_tokens=32)
    request = InferenceRequest(
        DeploymentTarget(dep),
        (Message(Role.USER, Content((TextContent("Hello"),))),),
        config,
    )
    snapshot = GenerationSupportSnapshot(
        request.target, (ParameterSupport(
            "max_output_tokens", CapabilitySupport(SupportLevel.NATIVE),
        ),),
    )
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep: "claude-mock-model"},
    )
    execution = service.invoke(request, snapshot)
    assert execution.response is not None
    assert execution.response.output.text == "synthetic-only"
    print("L7.5 Anthropic Messages:", execution.run.state.value)
    print("No Anthropic API request or billing occurred.")


if __name__ == "__main__":
    main()
