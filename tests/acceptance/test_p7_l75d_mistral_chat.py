"""P7-G5d Mistral Chat Completions contract and transport, offline only."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest

from pyllmkit.adapters.inference import (
    AdapterKey,
    AdapterRegistration,
    AdapterRegistry,
    CredentialRef,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
)
from pyllmkit.adapters.inference.mistral_chat import (
    AsyncMistralChatAdapter,
    MistralChatAdapter,
)
from pyllmkit.adapters.inference.mistral_chat_mapping import (
    decode_mistral_chat_response,
    encode_mistral_chat_request,
)
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    AsyncInferenceService,
    InferenceService,
    InvocationPortError,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    FinishReasonCode,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    InferenceRunState,
    ParameterSupport,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId

REF=CredentialRef("mistral-test")
CONFIG=ProviderConnectionConfig.mistral(REF)
MODEL="mistral-synthetic-model"
SECRET="FAKE-MISTRAL-SECRET"


def creds() -> EnvCredentialResolver:
    return EnvCredentialResolver({REF:"MISTRAL_API_KEY"},environ={"MISTRAL_API_KEY":SECRET})


def fixture(messages=None,cfg=None):  # type: ignore[no-untyped-def]
    c=InMemoryCatalog()
    txt=frozenset({Modality("text")})
    mods=ModalitySet(txt,txt)
    model,provider,dep=ModelId("demo-model"),ProviderId("mistral"),DeploymentId("mistral-cloud")
    c.models.register(Model(model,ModelIdentity(ModelFamily("mistral")),modalities=mods))
    c.providers.register(InferenceProvider(provider,"Mistral",modalities=mods))
    c.deployments.register(Deployment(
        dep,model,provider,DeploymentStatus.AVAILABLE,modalities=mods,runtime="cloud",
    ))
    if messages is None:
        messages=(Message(Role.USER,Content((TextContent("Bonjour"),))),)
    return c,dep,InferenceRequest(DeploymentTarget(dep),messages,cfg)


def snap(req):  # type: ignore[no-untyped-def]
    cfg=req.generation_config
    if cfg is None:
        return None
    names=("temperature","top_p","top_k","max_output_tokens","seed","stop_sequences","presence_penalty","frequency_penalty")
    return GenerationSupportSnapshot(req.target,tuple(
        ParameterSupport(n,CapabilitySupport(SupportLevel.NATIVE))
        for n in names if getattr(cfg,n) is not None
    ))


def prepared(messages=None,cfg=None):  # type: ignore[no-untyped-def]
    cat,dep,req=fixture(messages,cfg)
    fake=FakeInferenceAdapter()
    svc=InferenceService(
        DeploymentResolver(cat.models,cat.deployments,cat.providers),fake,{dep:MODEL},
    )
    assert svc.invoke(req,snap(req)).run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def native(text="Salut",reason="stop",usage="default"):  # type: ignore[no-untyped-def]
    data={
        "object":"chat.completion","model":MODEL,
        "choices":[{"index":0,"finish_reason":reason,
                    "message":{"role":"assistant","content":text,
                               "tool_calls":None,"prefix":False}}],
    }
    if usage=="default":
        data["usage"]={"prompt_tokens":8,"completion_tokens":3,"total_tokens":11}
    elif usage is not None:
        data["usage"]=usage
    return data


def reply(data=None,status=200,mime="application/json"):  # type: ignore[no-untyped-def]
    return httpx.Response(
        status,json=native() if data is None else data,
        headers={"content-type":mime},
    )


def service(transport,allow_live=True,resolver=None):  # type: ignore[no-untyped-def]
    c,dep,req=fixture()
    reg=AdapterRegistry()
    reg.register(AdapterRegistration(
        AdapterKey(ProviderId("mistral"),"cloud"),CONFIG,
        sync_factory=lambda cfg:MistralChatAdapter(
            cfg,creds() if resolver is None else resolver,
            allow_live=allow_live,_test_transport=transport,
        ),
    ))
    return InferenceService(
        DeploymentResolver(c.models,c.deployments,c.providers),
        RegisteredInferencePort(reg),{dep:MODEL},
    ),req


def test_mistral_golden_request_response_and_headers() -> None:
    calls=[]
    def handler(req: httpx.Request)->httpx.Response:
        calls.append(req)
        assert req.method=="POST"
        assert str(req.url)=="https://api.mistral.ai/v1/chat/completions"
        assert req.headers["authorization"]==f"Bearer {SECRET}"
        data=json.loads(req.content)
        assert data=={
            "model":MODEL,
            "messages":[{"role":"user","content":"Bonjour"}],
            "stream":False,"n":1,"tools":[],"tool_choice":"none",
            "parallel_tool_calls":False,"safe_prompt":False,
            "response_format":{"type":"text"},
        }
        return reply()
    svc,req=service(httpx.MockTransport(handler))
    out=svc.invoke(req)
    assert out.response is not None
    assert out.response.run_id==out.run.run_id
    assert out.response.output.text=="Salut"
    assert out.response.finish_reason is not None
    assert out.response.finish_reason.code is FinishReasonCode.STOP
    assert out.response.finish_reason.native_reason=="stop"
    assert out.response.usage is not None
    assert out.response.usage.input_tokens==8
    assert out.response.usage.output_tokens==3
    assert out.response.usage.total_tokens==11
    assert len(calls)==1
    assert SECRET not in repr(out)


def test_mistral_opt_in_off_never_contacts_network_or_secret() -> None:
    visited=[]
    empty=EnvCredentialResolver({REF:"MISTRAL_API_KEY"},environ={})
    svc,req=service(
        httpx.MockTransport(lambda r:(visited.append(r) or reply())),
        allow_live=False,resolver=empty,
    )
    result=svc.invoke(req)
    assert result.run.failure is not None and result.run.failure.code=="live_authorization_required"
    assert visited==[]


def test_mistral_roles_preserve_order_and_reject_developer_tool() -> None:
    messages=(
        Message(Role.SYSTEM,Content((TextContent("Be concise"),))),
        Message(Role.USER,Content((TextContent("One"),))),
        Message(Role.ASSISTANT,Content((TextContent("Two"),))),
        Message(Role.USER,Content((TextContent("Three"),))),
    )
    data=json.loads(encode_mistral_chat_request(prepared(messages=messages)))
    assert [m["role"] for m in data["messages"]]==["system","user","assistant","user"]
    assert [m["content"] for m in data["messages"]]==[
        "Be concise","One","Two","Three",
    ]
    for role in (Role.DEVELOPER,Role.TOOL):
        with pytest.raises(InvocationPortError,match="unsupported_message_role"):
            encode_mistral_chat_request(prepared(messages=(
                Message(role,Content((TextContent("x"),))),
            )))


def test_mistral_system_only_at_start_and_last_user() -> None:
    for messages in (
        (
            Message(Role.USER,Content((TextContent("one"),))),
            Message(Role.SYSTEM,Content((TextContent("two"),))),
            Message(Role.USER,Content((TextContent("three"),))),
        ),
        (Message(Role.ASSISTANT,Content((TextContent("no user"),))),),
    ):
        with pytest.raises(InvocationPortError,match="unsupported_message_structure"):
            encode_mistral_chat_request(prepared(messages=messages))


def test_mistral_multipart_and_multimodal_fail_closed() -> None:
    multipart=(Message(Role.USER,Content((TextContent("x"),TextContent("y")))),)
    with pytest.raises(InvocationPortError,match="unsupported_content_structure"):
        encode_mistral_chat_request(prepared(messages=multipart))
    from pyllmkit.domain.interactions import ImageContent, MediaSourceRef

    p=prepared()
    req=InferenceRequest(
        p.request.target,
        (Message(Role.USER,Content((ImageContent(MediaSourceRef("asset","img")),))),),
    )
    with pytest.raises(InvocationPortError,match="unsupported_input_modality"):
        encode_mistral_chat_request(replace(p,request=req))


def test_mistral_all_canonical_params_mapped_native_only() -> None:
    cfg=GenerationConfig(
        temperature=0.3,top_p=0.85,top_k=15,max_output_tokens=32,seed=5,
        stop_sequences=("END",),presence_penalty=0.2,frequency_penalty=0.4,
    )
    p=prepared(cfg=cfg)
    data=json.loads(encode_mistral_chat_request(p))
    for key,val in {
        "temperature":0.3,"top_p":0.85,"top_k":15,"max_tokens":32,
        "random_seed":5,"stop":["END"],"presence_penalty":0.2,"frequency_penalty":0.4,
    }.items():
        assert data[key]==val
    lost=replace(p,parameter_assessment=replace(p.parameter_assessment,assessments=()))
    with pytest.raises(InvocationPortError,match="unknown_generation_parameter"):
        encode_mistral_chat_request(lost)


@pytest.mark.parametrize("reason,code",[
    ("stop",FinishReasonCode.STOP),("length",FinishReasonCode.LENGTH),
    ("model_length",FinishReasonCode.UNKNOWN),("new_reason",FinishReasonCode.UNKNOWN),
])
def test_mistral_native_finish_reason_not_invented(reason,code):  # type: ignore[no-untyped-def]
    data=decode_mistral_chat_response(json.dumps(native(reason=reason)).encode(),prepared())
    assert data.finish_reason is not None
    assert data.finish_reason.code is code
    assert data.finish_reason.native_reason==reason


@pytest.mark.parametrize("reason,code",[
    ("tool_calls","unsupported_provider_output"),("tool_call","unsupported_provider_output"),
    ("error","provider_protocol_error"),
])
def test_mistral_tool_and_error_finish_not_success(reason,code):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError,match=code):
        decode_mistral_chat_response(json.dumps(native(reason=reason)).encode(),prepared())


@pytest.mark.parametrize("change,code",[
    ({"object":"response"},"provider_protocol_error"),
    ({"model":"different"},"provider_model_mismatch"),
    ({"choices":[]},"unsupported_provider_output"),
    ({"choices":[{},{}]},"unsupported_provider_output"),
    ({"choices":[42]},"provider_protocol_error"),
    ({"choices":[{"index":1,"message":{},"finish_reason":"stop"}]},"provider_protocol_error"),
    ({"choices":[{"index":0,"message":{},"finish_reason":None}]},"provider_not_completed"),
])
def test_mistral_invalid_envelope_fail_closed(change,code):  # type: ignore[no-untyped-def]
    n=native()
    n.update(change)
    with pytest.raises(InvocationPortError,match=code):
        decode_mistral_chat_response(json.dumps(n).encode(),prepared())


@pytest.mark.parametrize("change",[
    {"role":"tool"},
    {"content":[{"type":"text","text":"hello"}]},
    {"content":7},
    {"tool_calls":[{"function":{"name":"danger"}}]},
    {"reasoning_content":"PRIVATE"},
    {"refusal":"cannot"},
    {"audio":{"content":"PRIVATE"}},
    {"prefix":True},
])
def test_mistral_unsupported_message_semantics_rejected(change):  # type: ignore[no-untyped-def]
    n=native()
    n["choices"][0]["message"].update(change)
    with pytest.raises(InvocationPortError,match="unsupported_provider_output"):
        decode_mistral_chat_response(json.dumps(n).encode(),prepared())


def test_mistral_partial_usage_never_invents_totals() -> None:
    n=native(usage={"prompt_tokens":5})
    response=decode_mistral_chat_response(json.dumps(n).encode(),prepared())
    assert response.usage is not None
    assert response.usage.input_tokens==5
    assert response.usage.output_tokens is None
    assert response.usage.total_tokens is None
    no=decode_mistral_chat_response(json.dumps(native(usage=None)).encode(),prepared())
    assert no.usage is None
    c=decode_mistral_chat_response(json.dumps(native(usage={
        "prompt_tokens_details":{"cached_tokens":2},
    })).encode(),prepared())
    assert c.usage is not None and c.usage.cached_input_tokens==2


@pytest.mark.parametrize("usage",[
    [],{"prompt_tokens":-1},{"completion_tokens":True},
    {"total_tokens":"5"},{"prompt_tokens_details":[]},
    {"prompt_tokens_details":{"cached_tokens":-1}},
])
def test_mistral_invalid_usage_types_rejected(usage):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_mistral_chat_response(json.dumps(native(usage=usage)).encode(),prepared())


@pytest.mark.parametrize("status,code",[
    (302,"provider_protocol_error"),(400,"invalid_request"),(401,"authentication_failed"),
    (403,"permission_denied"),(404,"model_not_found"),(408,"provider_timeout"),
    (429,"rate_limited"),(503,"provider_overloaded"),
])
def test_mistral_transport_status_sanitized(status,code):  # type: ignore[no-untyped-def]
    svc,req=service(httpx.MockTransport(
        lambda _:reply({"detail":SECRET},status),
    ))
    failed=svc.invoke(req)
    assert failed.run.failure is not None and failed.run.failure.code==code
    assert SECRET not in repr(failed)


def test_mistral_missing_secret_never_opens_network() -> None:
    seen=[]
    missing=EnvCredentialResolver({REF:"MISTRAL_API_KEY"},environ={})
    svc,req=service(
        httpx.MockTransport(lambda r:(seen.append(r) or reply())),
        resolver=missing,
    )
    failed=svc.invoke(req)
    assert failed.run.failure is not None and failed.run.failure.code=="credential_unavailable"
    assert seen==[]


def test_mistral_async_success_and_default_off() -> None:
    c,dep,req=fixture()
    touched=[]
    async def mock(r:httpx.Request)->httpx.Response:
        touched.append(r)
        return reply()
    registry=AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("mistral"),"cloud"),CONFIG,
        async_factory=lambda cfg:AsyncMistralChatAdapter(
            cfg,creds(),allow_live=True,_test_transport=httpx.MockTransport(mock),
        ),
    ))
    service=AsyncInferenceService(
        DeploymentResolver(c.models,c.deployments,c.providers),
        RegisteredAsyncInferencePort(registry),{dep:MODEL},
    )
    run=asyncio.run(service.ainvoke(req))
    assert run.response is not None
    assert run.response.output.text=="Salut"
    assert run.response.run_id==run.run.run_id
    assert len(touched)==1
    with pytest.raises(InvocationPortError,match="live_authorization_required"):
        asyncio.run(AsyncMistralChatAdapter(CONFIG,creds()).ainvoke(prepared()))


def test_mistral_expired_deadlines_do_not_send() -> None:
    p=prepared()
    old=replace(p,context=replace(p.context,deadline=datetime(2000,1,1,tzinfo=UTC)))
    with pytest.raises(InvocationPortError,match="provider_timeout"):
        MistralChatAdapter(CONFIG,creds(),allow_live=True).invoke(old)
    with pytest.raises(InvocationPortError,match="provider_timeout"):
        asyncio.run(AsyncMistralChatAdapter(CONFIG,creds(),allow_live=True).ainvoke(old))


@pytest.mark.parametrize("exc,code",[
    (httpx.ReadTimeout("SECRET"),"provider_timeout"),
    (httpx.ConnectError("SECRET"),"connection_failure"),
    (httpx.RemoteProtocolError("SECRET"),"provider_protocol_error"),
])
def test_mistral_sync_native_errors_redacted(exc,code):  # type: ignore[no-untyped-def]
    def fail(_:httpx.Request)->httpx.Response:
        raise exc
    with pytest.raises(InvocationPortError,match=code) as error:
        MistralChatAdapter(CONFIG,creds(),allow_live=True,
            _test_transport=httpx.MockTransport(fail)).invoke(prepared())
    assert "SECRET" not in str(error.value)


@pytest.mark.parametrize("exc,code",[
    (httpx.ReadTimeout("SECRET"),"provider_timeout"),
    (httpx.ConnectError("SECRET"),"connection_failure"),
    (httpx.RemoteProtocolError("SECRET"),"provider_protocol_error"),
    (TimeoutError("SECRET"),"provider_timeout"),
])
def test_mistral_async_native_errors_redacted(exc,code):  # type: ignore[no-untyped-def]
    async def fail(_:httpx.Request)->httpx.Response:
        raise exc
    with pytest.raises(InvocationPortError,match=code) as err:
        asyncio.run(AsyncMistralChatAdapter(CONFIG,creds(),allow_live=True,
            _test_transport=httpx.MockTransport(fail)).ainvoke(prepared()))
    assert "SECRET" not in str(err.value)


def test_mistral_invalid_mime_oversized_reply() -> None:
    for data,mime,code in (
        (b"x"*2_097_153,"application/json","response_too_large"),
        (b"<html/>","text/html","provider_protocol_error"),
    ):
        res=httpx.Response(200,content=data,headers={"content-type":mime})
        svc,req=service(httpx.MockTransport(lambda _,expected=res:expected))
        outcome=svc.invoke(req)
        assert outcome.run.failure is not None and outcome.run.failure.code==code


def test_mistral_constructor_and_parser_strict_types() -> None:
    with pytest.raises(InvocationPortError,match="adapter_connection_invalid"):
        MistralChatAdapter(ProviderConnectionConfig.xai(REF),creds())
    with pytest.raises(InvocationPortError,match="credential_resolver_invalid"):
        MistralChatAdapter(CONFIG,object())  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="live_authorization_invalid"):
        MistralChatAdapter(CONFIG,creds(),allow_live=1)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="live_authorization_invalid"):
        AsyncMistralChatAdapter(CONFIG,creds(),allow_live="yes")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="adapter_protocol_error"):
        encode_mistral_chat_request(None)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="invalid_model_alias"):
        encode_mistral_chat_request(replace(prepared(),native_model_alias="bad\nmodel"))
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_mistral_chat_response(b"[]",prepared())
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_mistral_chat_response(b"{broken",prepared())
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_mistral_chat_response(
            b'{"object":"chat.completion","object":"chat.completion"}',prepared(),
        )


def test_mistral_unknown_finish_native_reason_sanitized() -> None:
    n=native(reason="future\nSECRET")
    result=decode_mistral_chat_response(json.dumps(n).encode(),prepared())
    assert result.finish_reason is not None
    assert result.finish_reason.code is FinishReasonCode.UNKNOWN
    assert result.finish_reason.native_reason is None
