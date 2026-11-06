"""P7 L7.2: explicit local connection policy with a fake, NO network."""

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    FakeInferenceAdapter,
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
    text = frozenset((Modality("text"),))
    modalities = ModalitySet(text, text)
    model = ModelId("synthetic-model")
    deployment = DeploymentId("synthetic-local")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("demo")), modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        deployment, model, status=DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime="ollama",
    ))
    registry = AdapterRegistry()
    fake = FakeInferenceAdapter("synthetic result; no model was contacted")
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"),
        ProviderConnectionConfig.ollama_local(),
        sync_factory=lambda _config: fake,
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry),
        {deployment: "explicit-local-alias"},
    )
    result = service.invoke(InferenceRequest(
        DeploymentTarget(deployment),
        (Message(Role.USER, Content((TextContent("offline ping"),))),),
    ))
    assert result.response is not None
    print(result.run.state.value, result.response.output.text)
    print("No network requests were made.")


if __name__ == "__main__":
    main()
