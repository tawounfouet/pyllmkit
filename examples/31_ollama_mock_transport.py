"""P7 L7.3 Ollama /api/chat example using HTTPX MockTransport, NO LIVE CALL."""

import json

import httpx

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    OllamaAdapter,
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


def main() -> None:
    catalog = InMemoryCatalog()
    modalities = ModalitySet(
        frozenset((Modality("text"),)), frozenset((Modality("text"),)),
    )
    model = ModelId("demo")
    deployment = DeploymentId("ollama-mock")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("offline")), modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        deployment, model, status=DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime="ollama",
    ))

    def mock_reply(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        assert data["stream"] is False
        assert data["think"] is False
        return httpx.Response(200, json={
            "model": data["model"], "done": True, "done_reason": "stop",
            "message": {"role": "assistant", "content": "Offline transport fixture"},
        })

    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=lambda connection: OllamaAdapter(
            connection, allow_live=True, _test_transport=httpx.MockTransport(mock_reply),
        ),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {deployment: "llama3.2:1b"},
    )
    outcome = service.invoke(InferenceRequest(
        DeploymentTarget(deployment),
        (Message(Role.USER, Content((TextContent("Hello"),))),),
    ))
    assert outcome.response is not None
    assert outcome.response.output.text == "Offline transport fixture"
    print("L7.3 Ollama mock:", outcome.run.state.value, "- no Ollama daemon called")


if __name__ == "__main__":
    main()
