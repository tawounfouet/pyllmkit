"""Google Gemini deterministic MockTransport example. No network or billing."""

import json

import httpx

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    CredentialRef,
    EnvCredentialResolver,
    RegisteredInferencePort,
)
from pyllmkit.adapters.inference.google_gemini import GoogleGeminiAdapter
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
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
    text = frozenset({Modality("text")})
    mods = ModalitySet(text,text)
    model, provider, dep = ModelId("gemini-demo"), ProviderId("google"), DeploymentId("google-offline")
    catalog.models.register(Model(model,ModelIdentity(ModelFamily("gemini")),modalities=mods))
    catalog.providers.register(InferenceProvider(provider,"Google",modalities=mods))
    catalog.deployments.register(Deployment(
        dep,model,provider,DeploymentStatus.AVAILABLE,modalities=mods,runtime="cloud",
    ))
    def reply(req: httpx.Request) -> httpx.Response:
        assert str(req.url).endswith("/gemini-synthetic:generateContent")
        body = json.loads(req.content)
        assert body["store"] is False
        return httpx.Response(200,json={
            "candidates":[{"finishReason":"STOP","content":{"role":"model","parts":[{"text":"mock-only"}]}}],
        },headers={"content-type":"application/json"})
    ref = CredentialRef("google-demo")
    resolver = EnvCredentialResolver({ref:"GEMINI_API_KEY"},environ={"GEMINI_API_KEY":"FAKE-KEY"})
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(provider,"cloud"),ProviderConnectionConfig.google(ref),
        sync_factory=lambda cfg: GoogleGeminiAdapter(
            cfg,resolver,allow_live=True,_test_transport=httpx.MockTransport(reply),
        ),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models,catalog.deployments,catalog.providers),
        RegisteredInferencePort(registry),{dep:"gemini-synthetic"},
    )
    result = service.invoke(InferenceRequest(
        DeploymentTarget(dep),(Message(Role.USER,Content((TextContent("hello"),))),),
    ))
    assert result.response is not None
    print("Google Gemini mock:",result.run.state.value,"- no cloud request")


if __name__ == "__main__":
    main()
