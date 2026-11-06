"""P7 six-provider offline registry: all explicit, no vendor networking."""

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    CredentialRef,
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
from pyllmkit.domain.providers import InferenceProvider, ProviderId


def main() -> None:
    catalog=InMemoryCatalog()
    modes=ModalitySet(frozenset({Modality("text")}),frozenset({Modality("text")}))
    connections={
        "ollama":ProviderConnectionConfig.ollama_local(),
        "openai":ProviderConnectionConfig.openai(CredentialRef("openai")),
        "anthropic":ProviderConnectionConfig.anthropic(CredentialRef("anthropic")),
        "google":ProviderConnectionConfig.google(CredentialRef("google")),
        "xai":ProviderConnectionConfig.xai(CredentialRef("xai")),
        "mistral":ProviderConnectionConfig.mistral(CredentialRef("mistral")),
    }
    registry=AdapterRegistry()
    alias={}
    for name,connection in connections.items():
        model,dep=ModelId(f"model-{name}"),DeploymentId(f"dep-{name}")
        catalog.models.register(Model(model,ModelIdentity(ModelFamily("synthetic")),modalities=modes))
        provider=None if name=="ollama" else ProviderId(name)
        if provider is not None:
            catalog.providers.register(InferenceProvider(provider,name,modalities=modes))
        runtime="ollama" if name=="ollama" else "cloud"
        catalog.deployments.register(Deployment(
            dep,model,provider,DeploymentStatus.AVAILABLE,
            modalities=modes,runtime=runtime,
        ))
        registry.register(AdapterRegistration(
            AdapterKey(provider,runtime),connection,
            sync_factory=lambda _cfg,label=name:FakeInferenceAdapter(f"OK:{label}"),
        ))
        alias[dep]=f"explicit-native-{name}"
    service=InferenceService(
        DeploymentResolver(catalog.models,catalog.deployments,catalog.providers),
        RegisteredInferencePort(registry),alias,
    )
    for dep in alias:
        result=service.invoke(InferenceRequest(
            DeploymentTarget(dep),
            (Message(Role.USER,Content((TextContent("offline"),))),),
        ))
        assert result.response is not None
        print(dep.value,":",result.response.output.text)
    print("6 providers routed locally, zero socket calls and zero real secrets.")


if __name__=="__main__":
    main()
