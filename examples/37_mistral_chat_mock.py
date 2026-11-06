"""Mistral Chat Completions offline MockTransport demo, no real calls."""

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
from pyllmkit.adapters.inference.mistral_chat import MistralChatAdapter
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
    c=InMemoryCatalog()
    txt=frozenset({Modality("text")})
    mods=ModalitySet(txt,txt)
    model,provider,dep=ModelId("demo"),ProviderId("mistral"),DeploymentId("mistral-offline")
    c.models.register(Model(model,ModelIdentity(ModelFamily("mistral")),modalities=mods))
    c.providers.register(InferenceProvider(provider,"Mistral AI",modalities=mods))
    c.deployments.register(Deployment(
        dep,model,provider,DeploymentStatus.AVAILABLE,modalities=mods,runtime="cloud",
    ))
    def mock(request:httpx.Request)->httpx.Response:
        payload=json.loads(request.content)
        assert payload["tools"] == []
        assert payload["tool_choice"] == "none"
        return httpx.Response(200,json={
            "object":"chat.completion","model":payload["model"],
            "choices":[{"index":0,"finish_reason":"stop",
                        "message":{"role":"assistant","content":"mistral mock"}}],
        },headers={"content-type":"application/json"})
    ref=CredentialRef("mistral-offline")
    resolver=EnvCredentialResolver({ref:"MISTRAL_API_KEY"},environ={"MISTRAL_API_KEY":"FAKE"})
    registry=AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(provider,"cloud"),ProviderConnectionConfig.mistral(ref),
        sync_factory=lambda cfg:MistralChatAdapter(
            cfg,resolver,allow_live=True,_test_transport=httpx.MockTransport(mock),
        ),
    ))
    svc=InferenceService(
        DeploymentResolver(c.models,c.deployments,c.providers),
        RegisteredInferencePort(registry),{dep:"mistral-synthetic-model"},
    )
    result=svc.invoke(InferenceRequest(
        DeploymentTarget(dep),(Message(Role.USER,Content((TextContent("hi"),))),),
    ))
    assert result.response is not None
    print("Mistral Chat mock:",result.response.output.text,"- no cloud request")


if __name__=="__main__":
    main()
