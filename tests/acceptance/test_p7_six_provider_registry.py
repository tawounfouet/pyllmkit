"""P7 six-provider composition smoke: six named routes, zero HTTP or API keys."""

import asyncio

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    AsyncFakeInferenceAdapter,
    CredentialRef,
    FakeInferenceAdapter,
    ProviderConnectionConfig,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
)
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import AsyncInferenceService, InferenceService
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import DeploymentId, DeploymentTarget, InferenceRequest
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId


def _six():  # type: ignore[no-untyped-def]
    catalog=InMemoryCatalog()
    modes=ModalitySet(frozenset({Modality("text")}),frozenset({Modality("text")}))
    connections={
        "openai": ProviderConnectionConfig.openai(CredentialRef("openai-fake")),
        "anthropic": ProviderConnectionConfig.anthropic(CredentialRef("anthropic-fake")),
        "google": ProviderConnectionConfig.google(CredentialRef("google-fake")),
        "xai": ProviderConnectionConfig.xai(CredentialRef("xai-fake")),
        "mistral": ProviderConnectionConfig.mistral(CredentialRef("mistral-fake")),
        "ollama": ProviderConnectionConfig.ollama_local(),
    }
    registry=AdapterRegistry()
    aliases={}
    for name,config in connections.items():
        model,dep=ModelId(f"model-{name}"),DeploymentId(f"deployment-{name}")
        catalog.models.register(Model(
            model,ModelIdentity(ModelFamily("testing")),modalities=modes,
        ))
        provider=None if name=="ollama" else ProviderId(name)
        if provider is not None:
            catalog.providers.register(InferenceProvider(
                provider,name,modalities=modes,
            ))
        runtime="ollama" if name=="ollama" else "cloud"
        catalog.deployments.register(Deployment(
            dep,model,provider,DeploymentStatus.AVAILABLE,
            modalities=modes,runtime=runtime,
        ))
        registry.register(AdapterRegistration(
            AdapterKey(provider,runtime),
            config,
            sync_factory=lambda _cfg,label=name: FakeInferenceAdapter(f"fake-{label}"),
            async_factory=lambda _cfg,label=name: AsyncFakeInferenceAdapter(f"fake-{label}"),
        ))
        aliases[dep]=f"native-alias-{name}"
    resolver=DeploymentResolver(catalog.models,catalog.deployments,catalog.providers)
    return resolver,registry,aliases


def test_all_six_providers_resolve_explicitly_sync_without_network() -> None:
    resolver,registry,aliases=_six()
    service=InferenceService(resolver,RegisteredInferencePort(registry),aliases)
    assert len(registry.list_keys())==6
    for dep in aliases:
        request=InferenceRequest(
            DeploymentTarget(dep),(Message(Role.USER,Content((TextContent("offline"),))),),
        )
        result=service.invoke(request)
        assert result.response is not None
        assert result.response.run_id==result.run.run_id
        assert result.response.output.text==f"fake-{dep.value.removeprefix('deployment-')}"


def test_all_six_providers_resolve_explicitly_async_without_network() -> None:
    resolver,registry,aliases=_six()
    service=AsyncInferenceService(
        resolver,RegisteredAsyncInferencePort(registry),aliases,
    )
    async def execute():  # type: ignore[no-untyped-def]
        for dep in aliases:
            result=await service.ainvoke(InferenceRequest(
                DeploymentTarget(dep),
                (Message(Role.USER,Content((TextContent("offline"),))),),
            ))
            assert result.response is not None
            assert result.response.output.text==f"fake-{dep.value.removeprefix('deployment-')}"
    asyncio.run(execute())
