"""P7 L7.4 Responses API example with MockTransport: zero cloud calls."""

import json

import httpx

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    CredentialRef,
    EnvCredentialResolver,
    OpenAIResponsesAdapter,
    ProviderConnectionConfig,
    RegisteredInferencePort,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import InferenceService
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, DeploymentTarget, InferenceRequest
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId


def main() -> None:
    catalog = InMemoryCatalog()
    modalities = ModalitySet(
        frozenset((Modality("text"),)), frozenset((Modality("text"),)),
    )
    model = ModelId("demo-model")
    dep = DeploymentId("openai-demo")
    provider = ProviderId("openai")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("demo")), modalities=modalities,
    ))
    catalog.providers.register(InferenceProvider(
        provider, "OpenAI", modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        dep, model, provider, DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime="cloud",
    ))

    def mock(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        assert data["store"] is False
        assert data["tools"] == []
        assert data["tool_choice"] == "none"
        return httpx.Response(200, json={
            "status": "completed", "model": data["model"],
            "output": [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": "mock-only"}],
            }],
        }, headers={"content-type": "application/json"})

    ref = CredentialRef("test")
    env = EnvCredentialResolver({ref: "OPENAI_API_KEY"}, environ={
        "OPENAI_API_KEY": "synthetic-not-real",
    })
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(provider, "cloud"), ProviderConnectionConfig.openai(ref),
        sync_factory=lambda config: OpenAIResponsesAdapter(
            config, env, allow_live=True,
            _test_transport=httpx.MockTransport(mock),
        ),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep: "gpt-4.1-mini"},
    )
    result = service.invoke(InferenceRequest(
        DeploymentTarget(dep), (Message(
            Role.USER, Content((TextContent("offline example"),)),
        ),),
    ))
    assert result.response is not None
    print("L7.4 OpenAI Responses mock:", result.response.output.text)
    print("No real provider request was sent.")


if __name__ == "__main__":
    main()
