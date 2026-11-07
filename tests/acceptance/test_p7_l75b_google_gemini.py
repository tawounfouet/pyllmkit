"""P7 Gemini extension: deterministic security, mapping, sync/async and negative tests."""

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
from pyllmkit.adapters.inference.cloud_http import (
    _headers,
    _httpx,
    _timeout,
    require_body_limit,
)
from pyllmkit.adapters.inference.google_gemini import (
    AsyncGoogleGeminiAdapter,
    GoogleGeminiAdapter,
)
from pyllmkit.adapters.inference.google_gemini_mapping import (
    decode_gemini_response,
    encode_gemini_request,
    gemini_model_alias,
)
from pyllmkit.adapters.inference.security import (
    ProviderConnectionConfig,
    ProviderProfile,
    SecurityConfigurationError,
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
from pyllmkit.domain.interactions import (
    Content,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
)
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId

REF = CredentialRef("gemini-offline")
CONFIG = ProviderConnectionConfig.google(REF)
ALIAS = "gemini-text-test"
SECRET = "GEMINI-SYNTHETIC-SECRET-NOT-REAL"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{ALIAS}:generateContent"


def creds() -> EnvCredentialResolver:
    return EnvCredentialResolver({REF: "GEMINI_API_KEY"}, environ={"GEMINI_API_KEY": SECRET})


def fixture(messages=None, generation=None):  # type: ignore[no-untyped-def]
    catalog = InMemoryCatalog()
    mods = ModalitySet(frozenset({Modality("text")}), frozenset({Modality("text")}))
    model = ModelId("google-domain-model")
    provider = ProviderId("google")
    dep = DeploymentId("google-cloud-dep")
    catalog.models.register(Model(model, ModelIdentity(ModelFamily("gemini")), modalities=mods))
    catalog.providers.register(InferenceProvider(provider, "Google AI", modalities=mods))
    catalog.deployments.register(Deployment(
        dep, model, provider, DeploymentStatus.AVAILABLE,
        modalities=mods, runtime="cloud",
    ))
    if messages is None:
        messages = (Message(Role.USER, Content((TextContent("Bonjour"),))),)
    return catalog, dep, InferenceRequest(DeploymentTarget(dep), messages, generation)


def snapshot(req):  # type: ignore[no-untyped-def]
    gen = req.generation_config
    if gen is None:
        return None
    names = (
        "temperature", "top_p", "top_k", "max_output_tokens",
        "seed", "stop_sequences", "presence_penalty", "frequency_penalty",
    )
    return GenerationSupportSnapshot(req.target, tuple(
        ParameterSupport(name, CapabilitySupport(SupportLevel.NATIVE))
        for name in names if getattr(gen, name) is not None
    ))


def prepared(messages=None, generation=None):  # type: ignore[no-untyped-def]
    c, dep, req = fixture(messages, generation)
    fake = FakeInferenceAdapter()
    service = InferenceService(
        DeploymentResolver(c.models, c.deployments, c.providers), fake,
        {dep: ALIAS},
    )
    assert service.invoke(req, snapshot(req)).run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def response(text="Salut", reason="STOP", usage="default"):  # type: ignore[no-untyped-def]
    data = {"candidates": [{
        "content": {"role": "model", "parts": [{"text": text}]},
        "finishReason": reason,
    }]}
    if usage == "default":
        data["usageMetadata"] = {
            "promptTokenCount": 7, "candidatesTokenCount": 3,
            "totalTokenCount": 10, "cachedContentTokenCount": 2,
            "thoughtsTokenCount": 0,
        }
    elif usage is not None:
        data["usageMetadata"] = usage
    return data


def reply(body=None, status=200, content_type="application/json"):  # type: ignore[no-untyped-def]
    return httpx.Response(
        status, json=response() if body is None else body,
        headers={"content-type": content_type},
    )


def service(transport, allow_live=True, resolver=None):  # type: ignore[no-untyped-def]
    catalog, dep, req = fixture()
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("google"), "cloud"), CONFIG,
        sync_factory=lambda cfg: GoogleGeminiAdapter(
            cfg, creds() if resolver is None else resolver,
            allow_live=allow_live, _test_transport=transport,
        ),
    ))
    return InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep: ALIAS},
    ), req


def test_gemini_profile_and_cloud_profiles_are_fail_closed() -> None:
    assert CONFIG.endpoint_url == "https://generativelanguage.googleapis.com/v1beta/models"
    assert CONFIG.profile is ProviderProfile.GOOGLE
    assert ProviderConnectionConfig.xai(REF).profile is ProviderProfile.XAI
    assert ProviderConnectionConfig.mistral(REF).profile is ProviderProfile.MISTRAL
    for profile, endpoint in (
        (ProviderProfile.GOOGLE, "https://generativelanguage.googleapis.com/v1beta/models/evil"),
        (ProviderProfile.XAI, "https://api.x.ai/v1/chat/completions"),
        (ProviderProfile.MISTRAL, "http://api.mistral.ai/v1/chat/completions"),
    ):
        with pytest.raises(SecurityConfigurationError, match="endpoint_not_approved"):
            ProviderConnectionConfig(profile, endpoint, REF)
    for profile, endpoint in (
        (ProviderProfile.GOOGLE, CONFIG.endpoint_url),
        (ProviderProfile.XAI, ProviderConnectionConfig.xai(REF).endpoint_url),
        (ProviderProfile.MISTRAL, ProviderConnectionConfig.mistral(REF).endpoint_url),
    ):
        with pytest.raises(SecurityConfigurationError, match="credential_reference_required"):
            ProviderConnectionConfig(profile, endpoint)
        with pytest.raises(SecurityConfigurationError, match="local_authorization_invalid"):
            ProviderConnectionConfig(profile, endpoint, REF, allow_local=True)


def test_gemini_no_network_before_opt_in_and_no_credentials_read() -> None:
    touched = []
    svc, request = service(httpx.MockTransport(lambda req: (
        touched.append(req) or reply()
    )), allow_live=False, resolver=EnvCredentialResolver({REF: "GEMINI_API_KEY"}, environ={}))
    outcome = svc.invoke(request)
    assert outcome.run.failure is not None
    assert outcome.run.failure.code == "live_authorization_required"
    assert touched == []


def test_gemini_request_and_response_mock_contract_sync() -> None:
    calls = []
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert str(request.url) == URL
        assert request.method == "POST"
        assert request.headers["x-goog-api-key"] == SECRET
        assert request.headers.get("authorization") is None
        wire = json.loads(request.content)
        assert wire == {
            "contents": [{"role": "user", "parts": [{"text": "Bonjour"}]}],
            "store": False,
            "generationConfig": {
                "candidateCount": 1, "responseMimeType": "text/plain",
            },
        }
        return reply()
    svc, request = service(httpx.MockTransport(handler))
    res = svc.invoke(request)
    assert res.run.state is InferenceRunState.COMPLETED
    assert res.response is not None
    assert res.response.run_id == res.run.run_id
    assert res.response.output.text == "Salut"
    assert res.response.finish_reason is not None
    assert res.response.finish_reason.code is FinishReasonCode.STOP
    assert res.response.usage is not None
    assert res.response.usage.input_tokens == 7
    assert res.response.usage.cached_input_tokens == 2
    assert res.response.usage.reasoning_tokens == 0
    assert res.response.usage.total_tokens == 10
    assert len(calls) == 1
    assert SECRET not in repr(res)


def test_gemini_system_role_and_sequence_preserved() -> None:
    msgs = (
        Message(Role.SYSTEM, Content((TextContent("You are precise"),))),
        Message(Role.USER, Content((TextContent("One"),))),
        Message(Role.ASSISTANT, Content((TextContent("Two"),))),
        Message(Role.USER, Content((TextContent("Three"),))),
    )
    data = json.loads(encode_gemini_request(prepared(messages=msgs)))
    assert data["systemInstruction"]["parts"][0]["text"] == "You are precise"
    assert [m["role"] for m in data["contents"]] == ["user", "model", "user"]
    assert [m["parts"][0]["text"] for m in data["contents"]] == ["One", "Two", "Three"]


@pytest.mark.parametrize("roles,code", [
    ((Role.DEVELOPER, Role.USER), "unsupported_message_role"),
    ((Role.TOOL, Role.USER), "unsupported_message_role"),
    ((Role.USER, Role.SYSTEM, Role.USER), "unsupported_message_structure"),
    ((Role.SYSTEM, Role.SYSTEM, Role.USER), "unsupported_message_structure"),
    ((Role.USER, Role.USER), "unsupported_message_structure"),
    ((Role.ASSISTANT, Role.USER), "unsupported_message_structure"),
    ((Role.USER, Role.ASSISTANT), "unsupported_message_structure"),
])
def test_gemini_invalid_conversation_refused(roles, code):  # type: ignore[no-untyped-def]
    messages = tuple(Message(role, Content((TextContent("x"),))) for role in roles)
    with pytest.raises(InvocationPortError, match=code):
        encode_gemini_request(prepared(messages=messages))


def test_gemini_multipart_and_modality_rejected_before_network() -> None:
    multi = (Message(Role.USER, Content((TextContent("one"), TextContent("two")))),)
    with pytest.raises(InvocationPortError, match="unsupported_content_structure"):
        encode_gemini_request(prepared(messages=multi))
    from pyllmkit.domain.interactions import ImageContent, MediaSourceRef
    old = prepared()
    invalid = InferenceRequest(
        old.request.target,
        (Message(Role.USER, Content((ImageContent(MediaSourceRef("asset", "demo")),))),),
    )
    with pytest.raises(InvocationPortError, match="unsupported_input_modality"):
        encode_gemini_request(replace(old, request=invalid))


def test_gemini_generation_parameters_canonical_and_native_attested() -> None:
    config = GenerationConfig(
        temperature=0.3, top_p=0.8, top_k=20, max_output_tokens=32,
        stop_sequences=("END",), seed=7, presence_penalty=0.2, frequency_penalty=0.1,
    )
    p = prepared(generation=config)
    wire = json.loads(encode_gemini_request(p))["generationConfig"]
    assert wire == {
        "candidateCount": 1, "responseMimeType": "text/plain",
        "temperature": 0.3, "topP": 0.8, "topK": 20, "maxOutputTokens": 32,
        "stopSequences": ["END"], "seed": 7,
        "presencePenalty": 0.2, "frequencyPenalty": 0.1,
    }
    altered = replace(p, parameter_assessment=replace(
        p.parameter_assessment, assessments=(),
    ))
    with pytest.raises(InvocationPortError, match="unknown_generation_parameter"):
        encode_gemini_request(altered)


@pytest.mark.parametrize("reason,code", [
    ("STOP", FinishReasonCode.STOP),
    ("MAX_TOKENS", FinishReasonCode.LENGTH),
    ("OTHER", FinishReasonCode.UNKNOWN),
    ("NEW_REASON", FinishReasonCode.UNKNOWN),
])
def test_gemini_finish_reason_is_mapped_explicitly(reason, code):  # type: ignore[no-untyped-def]
    result = decode_gemini_response(
        json.dumps(response(reason=reason)).encode(), prepared(),
    )
    assert result.finish_reason is not None
    assert result.finish_reason.code is code
    assert result.finish_reason.native_reason == reason


@pytest.mark.parametrize("reason", [
    "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT",
    "SPII", "IMAGE_SAFETY", "LANGUAGE",
])
def test_gemini_safety_filter_is_not_returned_as_success(reason):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError, match="provider_content_filtered"):
        decode_gemini_response(json.dumps(response(reason=reason)).encode(), prepared())


@pytest.mark.parametrize("reason,error", [
    ("MALFORMED_FUNCTION_CALL", "unsupported_provider_output"),
    ("FINISH_REASON_UNSPECIFIED", "provider_not_completed"),
])
def test_gemini_unrepresentable_finish_reason_fails_closed(reason, error):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError, match=error):
        decode_gemini_response(json.dumps(response(reason=reason)).encode(), prepared())


@pytest.mark.parametrize("change,error", [
    ({"candidates": []}, "unsupported_provider_output"),
    ({"candidates": [{}, {}]}, "unsupported_provider_output"),
    ({"candidates": [3]}, "provider_protocol_error"),
    ({"promptFeedback": {"blockReason": "SAFETY"}}, "provider_content_filtered"),
    ({"promptFeedback": []}, "provider_protocol_error"),
])
def test_gemini_invalid_envelopes_fail_closed(change, error):  # type: ignore[no-untyped-def]
    data = response()
    data.update(change)
    with pytest.raises(InvocationPortError, match=error):
        decode_gemini_response(json.dumps(data).encode(), prepared())


@pytest.mark.parametrize("candidate,error", [
    ({"finishReason": "STOP"}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "assistant", "parts": [{"text": "x"}]}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"functionCall": {"name": "run"}}]}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "x", "thought": True}]}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "x"}, {"text": "y"}]}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": []}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": 4}]}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "x"}]}, "groundingMetadata": {"url": "x"}}, "unsupported_provider_output"),
    ({"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": "x"}]}, "citationMetadata": {"citations": []}}, "unsupported_provider_output"),
])
def test_gemini_nontext_outputs_are_rejected(candidate, error):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError, match=error):
        decode_gemini_response(json.dumps({"candidates": [candidate]}).encode(), prepared())


def test_gemini_usage_partial_no_total_invented() -> None:
    result = decode_gemini_response(
        json.dumps(response(usage={"promptTokenCount": 4})).encode(), prepared(),
    )
    assert result.usage is not None
    assert result.usage.input_tokens == 4
    assert result.usage.output_tokens is None
    assert result.usage.total_tokens is None
    no_usage = decode_gemini_response(
        json.dumps(response(usage=None)).encode(), prepared(),
    )
    assert no_usage.usage is None


@pytest.mark.parametrize("usage", [
    [], {"promptTokenCount": -1}, {"candidatesTokenCount": True},
    {"totalTokenCount": "2"}, {"cachedContentTokenCount": -2},
    {"thoughtsTokenCount": 1.5},
])
def test_gemini_invalid_usage_type_refused(usage):  # type: ignore[no-untyped-def]
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_gemini_response(json.dumps(response(usage=usage)).encode(), prepared())


@pytest.mark.parametrize("status,code", [
    (302,"provider_protocol_error"), (400,"invalid_request"),
    (401,"authentication_failed"), (403,"permission_denied"),
    (404,"model_not_found"), (408,"provider_timeout"),
    (429,"rate_limited"), (503,"provider_overloaded"),
])
def test_gemini_http_errors_sanitized(status, code):  # type: ignore[no-untyped-def]
    svc, req = service(httpx.MockTransport(lambda _: reply(
        {"error": {"message": SECRET}}, status,
    )))
    res = svc.invoke(req)
    assert res.run.failure is not None and res.run.failure.code == code
    assert SECRET not in repr(res)


def test_gemini_missing_secret_and_wrong_connection_no_requests() -> None:
    calls = []
    missing = EnvCredentialResolver({REF: "GEMINI_API_KEY"}, environ={})
    svc, req = service(httpx.MockTransport(lambda r: (
        calls.append(r) or reply(),
    )), resolver=missing)
    assert svc.invoke(req).run.failure.code == "credential_unavailable"
    assert calls == []
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        GoogleGeminiAdapter(ProviderConnectionConfig.xai(REF), creds())
    with pytest.raises(InvocationPortError, match="credential_resolver_invalid"):
        GoogleGeminiAdapter(CONFIG, object())  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="live_authorization_invalid"):
        GoogleGeminiAdapter(CONFIG, creds(), allow_live=1)  # type: ignore[arg-type]


def test_gemini_async_mock_parity_with_explicit_registry() -> None:
    cat, dep, req = fixture()
    seen = []
    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return reply()
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("google"), "cloud"), CONFIG,
        async_factory=lambda cfg: AsyncGoogleGeminiAdapter(
            cfg, creds(), allow_live=True, _test_transport=httpx.MockTransport(handler),
        ),
    ))
    service = AsyncInferenceService(
        DeploymentResolver(cat.models, cat.deployments, cat.providers),
        RegisteredAsyncInferencePort(registry), {dep: ALIAS},
    )
    result = asyncio.run(service.ainvoke(req))
    assert result.response is not None
    assert result.response.output.text == "Salut"
    assert result.response.run_id == result.run.run_id
    assert len(seen) == 1


def test_gemini_async_default_refuses_live() -> None:
    with pytest.raises(InvocationPortError, match="live_authorization_required"):
        asyncio.run(AsyncGoogleGeminiAdapter(CONFIG, creds()).ainvoke(prepared()))


def test_gemini_request_size_and_timeout_bound_before_network() -> None:
    old = prepared()
    invalid = replace(old.request, messages=(Message(
        Role.USER, Content((TextContent("x" * 1_048_577),)),
    ),))
    with pytest.raises(InvocationPortError, match="request_too_large"):
        GoogleGeminiAdapter(CONFIG, creds(), allow_live=True).invoke(
            replace(old, request=invalid),
        )
    expired = replace(old, context=replace(
        old.context, deadline=datetime(2000, 1, 1, tzinfo=UTC),
    ))
    with pytest.raises(InvocationPortError, match="provider_timeout"):
        GoogleGeminiAdapter(CONFIG, creds(), allow_live=True).invoke(expired)


@pytest.mark.parametrize("failure,code", [
    (httpx.ReadTimeout("SENSITIVE"),"provider_timeout"),
    (httpx.ConnectError("SENSITIVE"),"connection_failure"),
    (httpx.RemoteProtocolError("SENSITIVE"),"provider_protocol_error"),
])
def test_gemini_sync_failures_no_exception_leak(failure,code):  # type: ignore[no-untyped-def]
    def fail(_: httpx.Request) -> httpx.Response:
        raise failure
    with pytest.raises(InvocationPortError, match=code) as err:
        GoogleGeminiAdapter(
            CONFIG, creds(), allow_live=True,
            _test_transport=httpx.MockTransport(fail),
        ).invoke(prepared())
    assert "SENSITIVE" not in str(err.value)


@pytest.mark.parametrize("failure,code", [
    (httpx.ReadTimeout("SENSITIVE"),"provider_timeout"),
    (httpx.ConnectError("SENSITIVE"),"connection_failure"),
    (httpx.RemoteProtocolError("SENSITIVE"),"provider_protocol_error"),
    (TimeoutError("SENSITIVE"),"provider_timeout"),
])
def test_gemini_async_failures_sanitized(failure,code):  # type: ignore[no-untyped-def]
    async def fail(_: httpx.Request) -> httpx.Response:
        raise failure
    with pytest.raises(InvocationPortError, match=code):
        asyncio.run(AsyncGoogleGeminiAdapter(
            CONFIG, creds(), allow_live=True,
            _test_transport=httpx.MockTransport(fail),
        ).ainvoke(prepared()))


def test_gemini_oversized_reply_and_bad_mime() -> None:
    for raw,typ,code in (
        (b"x" * 2_097_153,"application/json","response_too_large"),
        (b"bad","text/html","provider_protocol_error"),
    ):
        resp = httpx.Response(200,content=raw,headers={"content-type":typ})
        svc, req = service(httpx.MockTransport(lambda _,r=resp:r))
        assert svc.invoke(req).run.failure.code == code


def test_gemini_common_transport_rejects_unsupported_headers_and_bad_body() -> None:
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        _headers("secret","basic")
    with pytest.raises(InvocationPortError, match="request_too_large"):
        require_body_limit("not bytes")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="adapter_protocol_error"):
        _timeout(None,CONFIG)  # type: ignore[arg-type]


def test_gemini_invalid_alias_cannot_escape_google_model_path() -> None:
    initial = prepared()
    assert gemini_model_alias(initial) == ALIAS
    for alias in ("../metadata", "foo/bar", "x?key=abc", "%2e%2e", "foo:bar", "x\n", "x" * 129):
        tampered = replace(initial, native_model_alias=alias)
        with pytest.raises(InvocationPortError, match="invalid_model_alias"):
            encode_gemini_request(tampered)


def test_gemini_parser_does_not_echo_bad_json_or_duplicate_fields() -> None:
    old = prepared()
    for body in (b"not-json", b"[]", b'{"candidates":1,"candidates":2}'):
        with pytest.raises(InvocationPortError, match="provider_protocol_error"):
            decode_gemini_response(body, old)


def test_gemini_httpx_optional_and_secret_errors_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    from pyllmkit.adapters.inference.cloud_http import _secret
    actual = builtins.__import__
    def missing(name: str,*args: object,**kwargs: object) -> object:
        if name == "httpx":
            raise ImportError("SENSITIVE PATH")
        return actual(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",missing)
    with pytest.raises(InvocationPortError, match="optional_dependency_missing"):
        _httpx()
    monkeypatch.setattr(builtins,"__import__",actual)
    class Exploding:
        def resolve(self,ref):  # type: ignore[no-untyped-def]
            raise RuntimeError("SECRET_IN_ERROR")
    with pytest.raises(InvocationPortError, match="credential_unavailable") as exc:
        _secret(CONFIG,Exploding())  # type: ignore[arg-type]
    assert "SECRET_IN_ERROR" not in str(exc.value)


def test_cloud_destination_is_checked_again_after_app_validation() -> None:
    from pyllmkit.adapters.inference.cloud_http import _validate_destination

    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        _validate_destination(
            ProviderProfile.GOOGLE, CONFIG.endpoint_url,
            "https://generativelanguage.googleapis.com/v1beta/models/../metadata",
        )
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        _validate_destination(
            ProviderProfile.GOOGLE, CONFIG.endpoint_url, "https://evil.example/v1/responses",
        )
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        _validate_destination(
            ProviderProfile.XAI, ProviderConnectionConfig.xai(REF).endpoint_url,
            "https://evil.example/v1/responses",
        )
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        _validate_destination(
            ProviderProfile.MISTRAL, ProviderConnectionConfig.mistral(REF).endpoint_url,
            "https://api.mistral.ai/v1/chat/completions/extra",
        )
    _validate_destination(ProviderProfile.GOOGLE, CONFIG.endpoint_url, URL)
    _validate_destination(
        ProviderProfile.XAI, ProviderConnectionConfig.xai(REF).endpoint_url,
        ProviderConnectionConfig.xai(REF).endpoint_url,
    )


def test_gemini_multimodal_negative_mapping_branches_fail_closed() -> None:
    old = prepared()
    with pytest.raises(InvocationPortError, match="adapter_protocol_error"):
        encode_gemini_request(None)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_gemini_response(None, old)  # type: ignore[arg-type]

    invalid_system = Message(
        Role.SYSTEM,
        Content((ImageContent(MediaSourceRef("asset", "image-token")),)),
    )
    valid_user = Message(Role.USER, Content((TextContent("Salut"),)))
    bad = replace(
        old,
        request=InferenceRequest(old.request.target, (invalid_system, valid_user)),
    )
    with pytest.raises(InvocationPortError, match="unsupported_message_structure"):
        encode_gemini_request(bad)

    missing_finish = b'{"candidates":[{"content":{"parts":[{"text":"Salut"}]}}]}'
    with pytest.raises(InvocationPortError, match="provider_not_completed"):
        decode_gemini_response(missing_finish, old)
