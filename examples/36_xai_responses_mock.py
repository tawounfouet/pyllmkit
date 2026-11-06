"""xAI Grok Responses strict text demo: HTTPX MockTransport only, no billing."""

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
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.adapters.inference.xai_responses import XAIResponsesAdapter
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
    txt=frozenset({Modality("text")})
    mods=ModalitySet(txt,txt)
    model,provider,dep=ModelId("demo"),ProviderId("xai"),DeploymentId("grok-offline")
    catalog.models.register(Model(model,ModelIdentity(ModelFamily("grok")),modalities=mods))
    catalog.providers.register(InferenceProvider(provider,"xAI",modalities=mods))
    catalog.deployments.register(Deployment(
        dep,model,provider,DeploymentStatus.AVAILABLE,modalities=mods,runtime="cloud",
    ))
    def mock(request:httpx.Request)->httpx.Response:
        data=json.loads(request.content)
        assert data["store"] is False
        assert data["tools"]==[]
        return httpx.Response(200,json={
            "object":"response","model":data["model"],"status":"completed","store":False,
            "output":[{"type":"message","role":"assistant","status":"completed",
                       "content":[{"type":"output_text","text":"xai mock"}]}],
        },headers={"content-type":"application/json"})
    ref=CredentialRef("demo")
    resolver=EnvCredentialResolver({ref:"XAI_API_KEY"},environ={"XAI_API_KEY":"FAKE"})
    reg=AdapterRegistry()
    reg.register(AdapterRegistration(
        AdapterKey(provider,"cloud"),ProviderConnectionConfig.xai(ref),
        sync_factory=lambda cfg:XAIResponsesAdapter(
            cfg,resolver,allow_live=True,_test_transport=httpx.MockTransport(mock),
        ),
    ))
    svc=InferenceService(
        DeploymentResolver(catalog.models,catalog.deployments,catalog.providers),
        RegisteredInferencePort(reg),{dep:"grok-synthetic-text"},
    )
    out=svc.invoke(InferenceRequest(DeploymentTarget(dep),(
        Message(Role.USER,Content((TextContent("hello"),))),
    )))
    assert out.response is not None
    print("xAI Responses mock:",out.response.output.text,"- no cloud request")


if __name__=="__main__":
    main()
