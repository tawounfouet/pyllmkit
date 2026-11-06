"""P7-G5c xAI Responses contracts; no xAI network calls or credentials."""

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
from pyllmkit.adapters.inference.security import ProviderConnectionConfig
from pyllmkit.adapters.inference.xai_responses import (
    AsyncXAIResponsesAdapter,
    XAIResponsesAdapter,
)
from pyllmkit.adapters.inference.xai_responses_mapping import (
    decode_xai_responses_response,
    encode_xai_responses_request,
)
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

REF = CredentialRef("xai-offline")
CONFIG = ProviderConnectionConfig.xai(REF)
ALIAS = "grok-synthetic-text"
SECRET = "SYNTHETIC-SECRET-XAI"


def creds() -> EnvCredentialResolver:
    return EnvCredentialResolver({REF: "XAI_API_KEY"}, environ={"XAI_API_KEY": SECRET})


def fixture(messages=None,config=None):  # type: ignore[no-untyped-def]
    c = InMemoryCatalog()
    text = frozenset({Modality("text")})
    mods = ModalitySet(text, text)
    model, provider, dep = ModelId("grok"), ProviderId("xai"), DeploymentId("grok-cloud")
    c.models.register(Model(model, ModelIdentity(ModelFamily("grok")), modalities=mods))
    c.providers.register(InferenceProvider(provider, "xAI", modalities=mods))
    c.deployments.register(Deployment(
        dep, model, provider, DeploymentStatus.AVAILABLE,
        modalities=mods, runtime="cloud",
    ))
    if messages is None:
        messages = (Message(Role.USER, Content((TextContent("Bonjour"),))),)
    req = InferenceRequest(DeploymentTarget(dep), messages, config)
    return c, dep, req


def snapshot(req):  # type: ignore[no-untyped-def]
    cfg = req.generation_config
    if cfg is None:
        return None
    names = ("temperature", "top_p", "max_output_tokens", "top_k", "seed", "stop_sequences", "presence_penalty", "frequency_penalty")
    return GenerationSupportSnapshot(req.target, tuple(
        ParameterSupport(name, CapabilitySupport(SupportLevel.NATIVE))
        for name in names if getattr(cfg, name) is not None
    ))


def prepared(messages=None,config=None):  # type: ignore[no-untyped-def]
    c, dep, req = fixture(messages,config)
    fake = FakeInferenceAdapter()
    svc = InferenceService(
        DeploymentResolver(c.models,c.deployments,c.providers),fake,{dep:ALIAS},
    )
    assert svc.invoke(req,snapshot(req)).run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def native(text="Hello",usage="default"):  # type: ignore[no-untyped-def]
    data = {
        "object": "response", "status": "completed", "model": ALIAS,
        "store": False, "error": None,
        "output": [{
            "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
    }
    if usage == "default":
        data["usage"] = {
            "prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 20,
            "prompt_tokens_details": {"cached_tokens": 3},
            "completion_tokens_details": {"reasoning_tokens": 6},
        }
    elif usage is not None:
        data["usage"] = usage
    return data


def reply(data=None,status=200,mime="application/json"):  # type: ignore[no-untyped-def]
    return httpx.Response(
        status,json=native() if data is None else data,
        headers={"content-type":mime},
    )


def service(transport,allow_live=True,resolver=None):  # type: ignore[no-untyped-def]
    c,dep,req = fixture()
    reg = AdapterRegistry()
    reg.register(AdapterRegistration(
        AdapterKey(ProviderId("xai"),"cloud"),CONFIG,
        sync_factory=lambda cfg: XAIResponsesAdapter(
            cfg,creds() if resolver is None else resolver,
            allow_live=allow_live,_test_transport=transport,
        ),
    ))
    svc = InferenceService(
        DeploymentResolver(c.models,c.deployments,c.providers),
        RegisteredInferencePort(reg),{dep:ALIAS},
    )
    return svc,req


def test_xai_responses_request_privacy_golden_and_usage() -> None:
    calls = []
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert str(req.url) == "https://api.x.ai/v1/responses"
        assert req.method == "POST"
        assert req.headers["authorization"] == f"Bearer {SECRET}"
        payload = json.loads(req.content)
        assert payload == {
            "model":ALIAS,
            "input":[{"role":"user","content":"Bonjour"}],
            "store":False,"stream":False,"background":False,
            "tools":[],"tool_choice":"none","parallel_tool_calls":False,
            "truncation":"disabled","text":{"format":{"type":"text"}},
        }
        return reply()
    svc,req = service(httpx.MockTransport(handler))
    outcome = svc.invoke(req)
    assert outcome.run.state is InferenceRunState.COMPLETED
    assert outcome.response is not None
    assert outcome.response.run_id == outcome.run.run_id
    assert outcome.response.output.text == "Hello"
    assert outcome.response.finish_reason is not None
    assert outcome.response.finish_reason.code is FinishReasonCode.UNKNOWN
    assert outcome.response.usage is not None
    assert outcome.response.usage.input_tokens == 10
    assert outcome.response.usage.output_tokens == 4
    assert outcome.response.usage.total_tokens == 20
    assert outcome.response.usage.cached_input_tokens == 3
    assert outcome.response.usage.reasoning_tokens == 6
    assert len(calls) == 1
    assert SECRET not in repr(outcome)


def test_xai_roles_preserved_without_merging() -> None:
    messages = tuple(Message(r,Content((TextContent(str(i)),))) for i,r in enumerate(
        (Role.SYSTEM, Role.DEVELOPER, Role.USER, Role.ASSISTANT, Role.USER),
    ))
    data = json.loads(encode_xai_responses_request(prepared(messages=messages)))
    assert [x["role"] for x in data["input"]] == [
        "system","developer","user","assistant","user",
    ]
    assert [x["content"] for x in data["input"]] == ["0","1","2","3","4"]
    for role in (Role.TOOL,):
        with pytest.raises(InvocationPortError,match="unsupported_message_role"):
            encode_xai_responses_request(prepared(messages=(
                Message(role,Content((TextContent("x"),))),
            )))
    with pytest.raises(InvocationPortError,match="unsupported_content_structure"):
        encode_xai_responses_request(prepared(messages=(
            Message(Role.USER,Content((TextContent("a"),TextContent("b")))),
        )))


def test_xai_opt_in_disabled_never_reads_creds_or_network() -> None:
    contacted = []
    resolver = EnvCredentialResolver({REF:"XAI_API_KEY"},environ={})
    svc,req = service(httpx.MockTransport(
        lambda req: (contacted.append(req) or reply()),
    ),allow_live=False,resolver=resolver)
    result = svc.invoke(req)
    assert result.run.failure is not None
    assert result.run.failure.code == "live_authorization_required"
    assert contacted == []


def test_xai_parameter_support_requires_native_and_refuses_unknown() -> None:
    cfg = GenerationConfig(temperature=0.3, top_p=0.8,max_output_tokens=128)
    p = prepared(config=cfg)
    body = json.loads(encode_xai_responses_request(p))
    assert body["temperature"] == 0.3
    assert body["top_p"] == 0.8
    assert body["max_output_tokens"] == 128
    invalid = replace(p,parameter_assessment=replace(
        p.parameter_assessment,assessments=(),
    ))
    with pytest.raises(InvocationPortError,match="unknown_generation_parameter"):
        encode_xai_responses_request(invalid)
    for name,value in (
        ("top_k",12),("seed",42),("stop_sequences",("END",)),
        ("presence_penalty",0.1),("frequency_penalty",0.1),
    ):
        with pytest.raises(InvocationPortError,match="unsupported_generation_parameter"):
            encode_xai_responses_request(prepared(config=GenerationConfig(**{name:value})))


def test_xai_reasoning_items_must_not_be_silently_discarded() -> None:
    n = native()
    n["output"].append({
        "type":"reasoning", "status":"completed",
        "encrypted_content":"PRIVATE-OPAQUE-REASONING",
    })
    with pytest.raises(InvocationPortError,match="unsupported_provider_output"):
        decode_xai_responses_response(json.dumps(n).encode(),prepared())


@pytest.mark.parametrize("change,code",[
    ({"status":"incomplete"},"provider_not_completed"),
    ({"status":"in_progress"},"provider_not_completed"),
    ({"status":"future"},"provider_protocol_error"),
    ({"object":"chat.completion"},"provider_protocol_error"),
    ({"model":"different"},"provider_model_mismatch"),
    ({"store":True},"provider_privacy_policy_violation"),
    ({"error":{"message":"SECRET"}},"provider_protocol_error"),
    ({"incomplete_details":{"reason":"max_output_tokens"}},"provider_protocol_error"),
    ({"output":[]},"unsupported_provider_output"),
    ({"output":[{"type":"reasoning","status":"completed"}]},"unsupported_provider_output"),
    ({"output":[{"type":"function_call","name":"run"}]},"unsupported_provider_output"),
])
def test_xai_invalid_responses_rejected(change,code):  # type: ignore[no-untyped-def]
    n=native()
    n.update(change)
    with pytest.raises(InvocationPortError,match=code):
        decode_xai_responses_response(json.dumps(n).encode(),prepared())


@pytest.mark.parametrize("content",[
    [{"type":"refusal","refusal":"No"}],
    [{"type":"output_text","text":"x","annotations":[{"type":"url_citation"}]}],
    [{"type":"output_text","text":4}],
    [{"type":"output_text","text":"x","logprobs":[{"token":"x"}]}],
    [],
    [{"type":"output_text","text":"one"},{"type":"output_text","text":"two"}],
])
def test_xai_nontext_blocks_rejected(content):  # type: ignore[no-untyped-def]
    n=native()
    n["output"][0]["content"]=content
    with pytest.raises(InvocationPortError,match="unsupported_provider_output"):
        decode_xai_responses_response(json.dumps(n).encode(),prepared())


def test_xai_partial_usage_preserved_without_fake_totals() -> None:
    n=native(usage={"prompt_tokens":12})
    result=decode_xai_responses_response(json.dumps(n).encode(),prepared())
    assert result.usage is not None
    assert result.usage.input_tokens==12
    assert result.usage.output_tokens is None
    assert result.usage.total_tokens is None
    absent=decode_xai_responses_response(json.dumps(native(usage=None)).encode(),prepared())
    assert absent.usage is None
    cache=decode_xai_responses_response(json.dumps(native(usage={
        "prompt_tokens_details":{"cached_tokens":2},
    })).encode(),prepared())
    assert cache.usage is not None and cache.usage.cached_input_tokens==2


@pytest.mark.parametrize("usage",[
    [],{"prompt_tokens":-1},{"completion_tokens":True},
    {"total_tokens":"2"},{"prompt_tokens_details":4},
    {"completion_tokens_details":{"reasoning_tokens":-1}},
])
def test_xai_invalid_native_usage_rejected(usage):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_xai_responses_response(json.dumps(native(usage=usage)).encode(),prepared())


@pytest.mark.parametrize("status,code",[
    (302,"provider_protocol_error"),(400,"invalid_request"),
    (401,"authentication_failed"),(403,"permission_denied"),
    (404,"model_not_found"),(429,"rate_limited"),(503,"provider_overloaded"),
])
def test_xai_http_errors_redacted(status,code):  # type: ignore[no-untyped-def]
    svc,req=service(httpx.MockTransport(
        lambda _:reply({"error":{"message":SECRET}},status),
    ))
    failed=svc.invoke(req)
    assert failed.run.failure is not None and failed.run.failure.code==code
    assert SECRET not in repr(failed)


def test_xai_credential_errors_before_network() -> None:
    contacted=[]
    missing=EnvCredentialResolver({REF:"XAI_API_KEY"},environ={})
    svc,req=service(httpx.MockTransport(
        lambda r:(contacted.append(r) or reply()),
    ),resolver=missing)
    result=svc.invoke(req)
    assert result.run.failure is not None and result.run.failure.code=="credential_unavailable"
    assert contacted==[]


def test_xai_async_response_and_no_live_default() -> None:
    cat,dep,req=fixture()
    touched=[]
    async def handler(r: httpx.Request) -> httpx.Response:
        touched.append(r)
        return reply()
    registry=AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("xai"),"cloud"),CONFIG,
        async_factory=lambda cfg:AsyncXAIResponsesAdapter(
            cfg,creds(),allow_live=True,_test_transport=httpx.MockTransport(handler),
        ),
    ))
    service=AsyncInferenceService(
        DeploymentResolver(cat.models,cat.deployments,cat.providers),
        RegisteredAsyncInferencePort(registry),{dep:ALIAS},
    )
    result=asyncio.run(service.ainvoke(req))
    assert result.response is not None and result.response.output.text=="Hello"
    assert result.response.run_id==result.run.run_id
    assert len(touched)==1
    with pytest.raises(InvocationPortError,match="live_authorization_required"):
        asyncio.run(AsyncXAIResponsesAdapter(CONFIG,creds()).ainvoke(prepared()))


def test_xai_expired_deadline_no_network() -> None:
    p=prepared()
    old=replace(p,context=replace(p.context,deadline=datetime(2000,1,1,tzinfo=UTC)))
    with pytest.raises(InvocationPortError,match="provider_timeout"):
        XAIResponsesAdapter(CONFIG,creds(),allow_live=True).invoke(old)
    with pytest.raises(InvocationPortError,match="provider_timeout"):
        asyncio.run(AsyncXAIResponsesAdapter(CONFIG,creds(),allow_live=True).ainvoke(old))


@pytest.mark.parametrize("exc,code",[
    (httpx.ReadTimeout("SECRET-NATIVE"),"provider_timeout"),
    (httpx.ConnectError("SECRET-NATIVE"),"connection_failure"),
    (httpx.RemoteProtocolError("SECRET-NATIVE"),"provider_protocol_error"),
])
def test_xai_sync_errors_sanitized(exc,code):  # type: ignore[no-untyped-def]
    def fail(_:httpx.Request)->httpx.Response:
        raise exc
    with pytest.raises(InvocationPortError,match=code) as err:
        XAIResponsesAdapter(CONFIG,creds(),allow_live=True,
            _test_transport=httpx.MockTransport(fail)).invoke(prepared())
    assert "SECRET-NATIVE" not in str(err.value)


@pytest.mark.parametrize("exc,code",[
    (httpx.ReadTimeout("SECRET-NATIVE"),"provider_timeout"),
    (httpx.ConnectError("SECRET-NATIVE"),"connection_failure"),
    (httpx.RemoteProtocolError("SECRET-NATIVE"),"provider_protocol_error"),
    (TimeoutError("SECRET-NATIVE"),"provider_timeout"),
])
def test_xai_async_errors_sanitized(exc,code):  # type: ignore[no-untyped-def]
    async def fail(_:httpx.Request)->httpx.Response:
        raise exc
    with pytest.raises(InvocationPortError,match=code):
        asyncio.run(AsyncXAIResponsesAdapter(CONFIG,creds(),allow_live=True,
            _test_transport=httpx.MockTransport(fail)).ainvoke(prepared()))


def test_xai_bad_reply_size_and_content_type() -> None:
    for raw,typ,code in [
        (b"x"*2_097_153,"application/json","response_too_large"),
        (b"bad","text/html","provider_protocol_error"),
    ]:
        response=httpx.Response(200,content=raw,headers={"content-type":typ})
        svc,req=service(httpx.MockTransport(lambda _,r=response:r))
        assert svc.invoke(req).run.failure.code==code


def test_xai_invalid_constructor_and_wire_input_types() -> None:
    with pytest.raises(InvocationPortError,match="adapter_connection_invalid"):
        XAIResponsesAdapter(ProviderConnectionConfig.google(REF),creds())
    with pytest.raises(InvocationPortError,match="credential_resolver_invalid"):
        XAIResponsesAdapter(CONFIG,object())  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="live_authorization_invalid"):
        XAIResponsesAdapter(CONFIG,creds(),allow_live=1)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="live_authorization_invalid"):
        AsyncXAIResponsesAdapter(CONFIG,creds(),allow_live="yes")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="adapter_protocol_error"):
        encode_xai_responses_request(None)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError,match="invalid_model_alias"):
        encode_xai_responses_request(replace(prepared(),native_model_alias="bad\nmodel"))
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_xai_responses_response(b"[]",prepared())
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_xai_responses_response(b"{broken",prepared())
    with pytest.raises(InvocationPortError,match="provider_protocol_error"):
        decode_xai_responses_response(b'{"object":"response","object":"response"}',prepared())


def test_xai_raw_multimodal_input_rejected_even_if_application_bypassed() -> None:
    from pyllmkit.domain.interactions import ImageContent, MediaSourceRef

    p=prepared()
    req=InferenceRequest(p.request.target,(
        Message(Role.USER,Content((ImageContent(MediaSourceRef("asset","image")),))),
    ))
    with pytest.raises(InvocationPortError,match="unsupported_input_modality"):
        encode_xai_responses_request(replace(p,request=req))
