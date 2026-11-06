"""P7-AC-025..032. Offline Responses API acceptance with HTTPX MockTransport."""

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
    AsyncOpenAIResponsesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    OpenAIResponsesAdapter,
    ProviderConnectionConfig,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
)
from pyllmkit.adapters.inference.openai_responses_mapping import (
    decode_openai_responses_response,
    encode_openai_responses_request,
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

_REF = CredentialRef("openai-test")
_CONFIG = ProviderConnectionConfig.openai(_REF)
_SECRET = "sk-SECRET-CANARY-not-real"


def _resolver() -> EnvCredentialResolver:
    return EnvCredentialResolver(
        {_REF: "OPENAI_API_KEY"},
        environ={"OPENAI_API_KEY": _SECRET},
    )


def _catalog(
    messages: tuple[Message, ...] | None = None,
    generation: GenerationConfig | None = None,
) -> tuple[InMemoryCatalog, DeploymentId, InferenceRequest]:
    c = InMemoryCatalog()
    text = frozenset((Modality("text"),))
    modalities = ModalitySet(text, text)
    model = ModelId("gpt-model")
    provider = ProviderId("openai")
    deployment = DeploymentId("openai-deployment")
    c.models.register(Model(model, ModelIdentity(ModelFamily("gpt")), modalities=modalities))
    c.providers.register(InferenceProvider(provider, "OpenAI", modalities=modalities))
    c.deployments.register(Deployment(
        deployment, model, provider, DeploymentStatus.AVAILABLE,
        modalities=modalities, runtime="cloud",
    ))
    if messages is None:
        messages = (Message(Role.USER, Content((TextContent("Bonjour"),))),)
    request = InferenceRequest(DeploymentTarget(deployment), messages, generation)
    return c, deployment, request


def _prepared(
    messages: tuple[Message, ...] | None = None,
    generation: GenerationConfig | None = None,
    snapshot: GenerationSupportSnapshot | None = None,
):  # type: ignore[no-untyped-def]
    c, dep, request = _catalog(messages, generation)
    fake = FakeInferenceAdapter()
    svc = InferenceService(
        DeploymentResolver(c.models, c.deployments, c.providers),
        fake, {dep: "gpt-4.1-mini"},
    )
    result = svc.invoke(request, snapshot)
    assert result.run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def _native(
    text: str = "Salut",
    *,
    usage: object = "default",
) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "resp_test",
        "object": "response",
        "status": "completed",
        "model": "gpt-4.1-mini",
        "error": None,
        "incomplete_details": None,
        "output": [{
            "type": "message", "status": "completed", "role": "assistant",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
    }
    if usage == "default":
        data["usage"] = {
            "input_tokens": 5, "output_tokens": 3, "total_tokens": 8,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        }
    elif usage is not None:
        data["usage"] = usage
    return data


def _response(data: dict[str, object] | None = None, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status, json=_native() if data is None else data,
        headers={"content-type": "application/json"},
    )


def _service(
    transport: httpx.MockTransport,
    *,
    allow_live: bool = True,
    credentials: EnvCredentialResolver | None = None,
) -> tuple[InferenceService, InferenceRequest]:
    catalog, dep, request = _catalog()
    registry = AdapterRegistry()
    resolver = _resolver() if credentials is None else credentials
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("openai"), "cloud"), _CONFIG,
        sync_factory=lambda cfg: OpenAIResponsesAdapter(
            cfg, resolver, allow_live=allow_live, _test_transport=transport,
        ),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep: "gpt-4.1-mini"},
    )
    return service, request


def test_p7_ac025_disabled_by_default_without_credential_or_http_contact() -> None:
    visited: list[httpx.Request] = []
    def responder(request: httpx.Request) -> httpx.Response:
        visited.append(request)
        return _response()
    service, request = _service(httpx.MockTransport(responder), allow_live=False)
    result = service.invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == "live_authorization_required"
    assert visited == []


def test_p7_ac026_sync_request_privacy_and_golden_response() -> None:
    calls: list[httpx.Request] = []
    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST"
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == f"Bearer {_SECRET}"
        payload = json.loads(request.content)
        assert payload == {
            "model": "gpt-4.1-mini",
            "input": [{"role": "user", "content": "Bonjour"}],
            "store": False, "stream": False, "background": False,
            "tools": [], "tool_choice": "none", "parallel_tool_calls": False,
            "truncation": "disabled",
            "text": {"format": {"type": "text"}},
        }
        return _response()
    service, request = _service(httpx.MockTransport(responder))
    result = service.invoke(request)
    assert result.run.state is InferenceRunState.COMPLETED
    assert result.response is not None
    assert result.response.output.text == "Salut"
    assert result.response.run_id == result.run.run_id
    assert result.response.finish_reason is not None
    assert result.response.finish_reason.code is FinishReasonCode.UNKNOWN
    assert result.response.usage is not None
    assert result.response.usage.input_tokens == 5
    assert result.response.usage.output_tokens == 3
    assert result.response.usage.total_tokens == 8
    assert result.response.usage.cached_input_tokens == 0
    assert len(calls) == 1
    assert _SECRET not in repr(result)


def test_p7_ac027_roles_and_order_preserved_without_instruction_merging() -> None:
    messages = (
        Message(Role.SYSTEM, Content((TextContent("A"),))),
        Message(Role.DEVELOPER, Content((TextContent("B"),))),
        Message(Role.USER, Content((TextContent("C"),))),
        Message(Role.ASSISTANT, Content((TextContent("D"),))),
    )
    payload = json.loads(encode_openai_responses_request(_prepared(messages)))
    assert payload["input"] == [
        {"role": "system", "content": "A"},
        {"role": "developer", "content": "B"},
        {"role": "user", "content": "C"},
        {"role": "assistant", "content": "D"},
    ]
    for role in (Role.TOOL,):
        prepared = _prepared((Message(role, Content((TextContent("tool-result"),))),))
        with pytest.raises(InvocationPortError, match="unsupported_message_role"):
            encode_openai_responses_request(prepared)
    multiple = _prepared((Message(
        Role.USER, Content((TextContent("one"), TextContent("two"))),
    ),))
    with pytest.raises(InvocationPortError, match="unsupported_content_structure"):
        encode_openai_responses_request(multiple)


def test_p7_ac028_explicit_supported_options_and_unknown_params_rejected() -> None:
    generation = GenerationConfig(
        temperature=0.5, top_p=0.9, max_output_tokens=64,
    )
    _, _, req = _catalog(generation=generation)
    snapshot = GenerationSupportSnapshot(
        req.target, tuple(ParameterSupport(
            key, CapabilitySupport(SupportLevel.NATIVE),
        ) for key in ("temperature", "top_p", "max_output_tokens")),
    )
    payload = json.loads(encode_openai_responses_request(
        _prepared(generation=generation, snapshot=snapshot),
    ))
    assert payload["temperature"] == 0.5
    assert payload["top_p"] == 0.9
    assert payload["max_output_tokens"] == 64
    for name, value in (("top_k", 3), ("seed", 5), ("stop_sequences", ("x",))):
        gen = GenerationConfig(**{name: value})
        _, _, sample = _catalog(generation=gen)
        snap = GenerationSupportSnapshot(
            sample.target, (ParameterSupport(
                name, CapabilitySupport(SupportLevel.NATIVE),
            ),),
        )
        with pytest.raises(InvocationPortError, match="unsupported_generation_parameter"):
            encode_openai_responses_request(_prepared(generation=gen, snapshot=snap))


@pytest.mark.parametrize("change,code", [
    ({"status": "incomplete"}, "provider_not_completed"),
    ({"status": "failed"}, "provider_not_completed"),
    ({"status": "queued"}, "provider_not_completed"),
    ({"model": "different"}, "provider_model_mismatch"),
    ({"error": {"message": "SECRET"}}, "provider_protocol_error"),
    ({"incomplete_details": {"reason": "max_output_tokens"}}, "provider_protocol_error"),
    ({"output": [{"type": "function_call", "name": "unsafe", "arguments": "{}"}]}, "unsupported_provider_output"),
    ({"output": [{"type": "reasoning", "summary": []}]}, "unsupported_provider_output"),
    ({"output": []}, "unsupported_provider_output"),
    ({"output": [123]}, "unsupported_provider_output"),
])
def test_p7_ac029_reject_noncomplete_or_nontyped_output(
    change: dict[str, object], code: str,
) -> None:
    data = _native()
    data.update(change)
    with pytest.raises(InvocationPortError, match=code):
        decode_openai_responses_response(json.dumps(data).encode(), _prepared())


@pytest.mark.parametrize("content,code", [
    ([{"type": "refusal", "refusal": "no"}], "unsupported_provider_output"),
    ([{"type": "output_text", "text": 7}], "unsupported_provider_output"),
    ([{"type": "output_text", "text": "x", "annotations": [{"type": "url_citation"}]}], "unsupported_provider_output"),
    ([{"type": "output_text", "text": "x", "logprobs": [{"token": "x"}]}], "unsupported_provider_output"),
    ([], "unsupported_provider_output"),
])
def test_p7_ac029_content_blocks_fail_closed(
    content: list[dict[str, object]], code: str,
) -> None:
    data = _native()
    data["output"] = [{
        "type": "message", "role": "assistant", "status": "completed",
        "content": content,
    }]
    with pytest.raises(InvocationPortError, match=code):
        decode_openai_responses_response(json.dumps(data).encode(), _prepared())


def test_p7_ac029_partial_usage_and_no_fake_totals() -> None:
    data = _native(usage={"input_tokens": 2})
    result = decode_openai_responses_response(json.dumps(data).encode(), _prepared())
    assert result.usage is not None
    assert result.usage.input_tokens == 2
    assert result.usage.output_tokens is None
    assert result.usage.total_tokens is None
    data = _native(usage=None)
    result = decode_openai_responses_response(json.dumps(data).encode(), _prepared())
    assert result.usage is None
    data["usage"] = {"output_tokens": 4, "output_tokens_details": {"reasoning_tokens": 2}}
    result = decode_openai_responses_response(json.dumps(data).encode(), _prepared())
    assert result.usage is not None
    assert result.usage.reasoning_tokens == 2


@pytest.mark.parametrize("status,code", [
    (302, "provider_protocol_error"), (400, "invalid_request"),
    (401, "authentication_failed"), (403, "permission_denied"),
    (404, "model_not_found"), (408, "provider_timeout"),
    (429, "rate_limited"), (500, "provider_overloaded"),
])
def test_p7_ac030_http_errors_are_safe_and_do_not_echo_bodies(
    status: int, code: str,
) -> None:
    service, request = _service(httpx.MockTransport(
        lambda _: _response({"error": {"message": _SECRET}}, status),
    ))
    result = service.invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == code
    assert _SECRET not in str(result.run.failure)
    assert _SECRET not in repr(result)


def test_p7_ac030_missing_secret_or_bad_resolver_never_contacts_network() -> None:
    calls: list[httpx.Request] = []
    transport = httpx.MockTransport(lambda req: (
        calls.append(req) or _response()
    ))
    missing = EnvCredentialResolver({_REF: "OPENAI_API_KEY"}, environ={})
    service, req = _service(transport, credentials=missing)
    outcome = service.invoke(req)
    assert outcome.run.failure is not None
    assert outcome.run.failure.code == "credential_unavailable"
    assert calls == []


def test_p7_ac031_async_parity_with_mocked_response() -> None:
    catalog, deployment, request = _catalog()
    seen: list[httpx.Request] = []
    async def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return _response()
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("openai"), "cloud"), _CONFIG,
        async_factory=lambda cfg: AsyncOpenAIResponsesAdapter(
            cfg, _resolver(), allow_live=True,
            _test_transport=httpx.MockTransport(handler),
        ),
    ))
    service = AsyncInferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredAsyncInferencePort(registry), {deployment: "gpt-4.1-mini"},
    )
    result = asyncio.run(service.ainvoke(request))
    assert result.response is not None
    assert result.response.run_id == result.run.run_id
    assert result.response.output.text == "Salut"
    assert len(seen) == 1


def test_p7_ac031_async_disabled_by_default() -> None:
    prepared = _prepared()
    adapter = AsyncOpenAIResponsesAdapter(_CONFIG, _resolver())
    with pytest.raises(InvocationPortError, match="live_authorization_required"):
        asyncio.run(adapter.ainvoke(prepared))


def test_p7_ac032_expired_deadline_and_bounded_response() -> None:
    prepared = _prepared()
    expired = replace(
        prepared, context=replace(
            prepared.context, deadline=datetime(2000, 1, 1, tzinfo=UTC),
        ),
    )
    touched: list[httpx.Request] = []
    adapter = OpenAIResponsesAdapter(
        _CONFIG, _resolver(), allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda req: (touched.append(req) or _response()),
        ),
    )
    with pytest.raises(InvocationPortError, match="provider_timeout"):
        adapter.invoke(expired)
    assert touched == []
    giant = b"x" * 2_097_153
    large = OpenAIResponsesAdapter(
        _CONFIG, _resolver(), allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, content=giant, headers={"content-type": "application/json"},
            ),
        ),
    )
    with pytest.raises(InvocationPortError, match="response_too_large"):
        large.invoke(prepared)


def test_p7_ac032_transport_timeout_and_connection_error_redacted() -> None:
    prepared = _prepared()
    for error, code in (
        (httpx.ConnectError("APIKEY_SECRET"), "connection_failure"),
        (httpx.ReadTimeout("APIKEY_SECRET"), "provider_timeout"),
        (httpx.RemoteProtocolError("APIKEY_SECRET"), "provider_protocol_error"),
    ):
        def responder(_: httpx.Request, exc: Exception = error) -> httpx.Response:
            raise exc
        adapter = OpenAIResponsesAdapter(
            _CONFIG, _resolver(), allow_live=True,
            _test_transport=httpx.MockTransport(responder),
        )
        with pytest.raises(InvocationPortError, match=code) as exc:
            adapter.invoke(prepared)
        assert "APIKEY_SECRET" not in str(exc.value)


def test_openai_optional_http_dependency_missing_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    from pyllmkit.adapters.inference.openai_responses import _httpx

    real_import = builtins.__import__

    def import_override(name: str, *args: object, **kwargs: object) -> object:
        if name == "httpx":
            raise ImportError("LOCAL_SECRET_IN_PATH")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_override)
    with pytest.raises(InvocationPortError, match="optional_dependency_missing") as exc:
        _httpx()
    assert "LOCAL_SECRET" not in str(exc.value)


def test_openai_rejects_bad_configuration_and_resolver_before_network() -> None:
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        OpenAIResponsesAdapter(
            ProviderConnectionConfig.ollama_local(), _resolver(), allow_live=True,
        )
    with pytest.raises(InvocationPortError, match="credential_resolver_invalid"):
        OpenAIResponsesAdapter(_CONFIG, object())  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="live_authorization_invalid"):
        OpenAIResponsesAdapter(_CONFIG, _resolver(), allow_live="yes")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="live_authorization_invalid"):
        AsyncOpenAIResponsesAdapter(_CONFIG, _resolver(), allow_live=1)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        AsyncOpenAIResponsesAdapter(
            ProviderConnectionConfig.ollama_local(), _resolver(),
        )


def test_openai_guarded_connection_catches_tampering() -> None:
    from pyllmkit.adapters.inference.openai_responses import _validate

    for field_name, value in (
        ("endpoint_url", "https://evil.example/v1/responses"),
        ("credential_ref", None),
        ("verify_tls", False),
        ("follow_redirects", True),
        ("allow_local", True),
    ):
        config = ProviderConnectionConfig.openai(_REF)
        object.__setattr__(config, field_name, value)
        with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
            _validate(config, _resolver())


def test_openai_secret_resolver_cannot_return_raw_or_unvalidated_data() -> None:
    from pyllmkit.adapters.inference.openai_responses import _authorize_secret

    class RawResolver:
        def resolve(self, reference: CredentialRef) -> str:
            return _SECRET

    class Raises:
        def resolve(self, reference: CredentialRef) -> object:
            raise RuntimeError("SECRET_ALREADY_LEAKED")

    with pytest.raises(InvocationPortError, match="credential_unavailable"):
        _authorize_secret(_CONFIG, RawResolver())  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="credential_unavailable") as exc:
        _authorize_secret(_CONFIG, Raises())  # type: ignore[arg-type]
    assert "SECRET_ALREADY_LEAKED" not in str(exc.value)

    wrong_config = ProviderConnectionConfig.openai(_REF)
    object.__setattr__(wrong_config, "credential_ref", None)
    with pytest.raises(InvocationPortError, match="credential_unavailable"):
        _authorize_secret(wrong_config, _resolver())


def test_openai_rejects_invalid_mapper_inputs_and_untrusted_model_alias() -> None:
    prepared = _prepared()
    with pytest.raises(InvocationPortError, match="adapter_protocol_error"):
        encode_openai_responses_request(None)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="invalid_model_alias"):
        encode_openai_responses_request(replace(prepared, native_model_alias="bad\nmodel"))
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(None, prepared)  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(b"{}", "wrong")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(b"{not json}", prepared)
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(b"[]", prepared)
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(
            b'{"status":"completed","status":"completed"}', prepared,
        )


def test_openai_refuses_nontext_content_at_wire_boundary() -> None:
    from pyllmkit.domain.interactions import ImageContent, MediaSourceRef

    original = _prepared()
    request = InferenceRequest(
        original.request.target,
        (Message(Role.USER, Content((ImageContent(MediaSourceRef("asset", "pic")),))),),
    )
    with pytest.raises(InvocationPortError, match="unsupported_input_modality"):
        encode_openai_responses_request(replace(original, request=request))


@pytest.mark.parametrize("usage", (
    {"input_tokens": -1},
    {"output_tokens": True},
    {"total_tokens": "3"},
    {"input_tokens_details": 7},
    {"output_tokens_details": {"reasoning_tokens": -1}},
))
def test_openai_refuses_invalid_native_usage(usage: dict[str, object]) -> None:
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(
            json.dumps(_native(usage=usage)).encode(), _prepared(),
        )


def test_openai_non_object_usage_or_output_status_is_rejected() -> None:
    bad = _native()
    bad["usage"] = []
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(json.dumps(bad).encode(), _prepared())
    bad = _native()
    bad["status"] = "future_status"
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_openai_responses_response(json.dumps(bad).encode(), _prepared())
    for change in (
        {"output": [{"type": "message", "role": "user", "status": "completed", "content": []}]},
        {"output": [{"type": "message", "role": "assistant", "status": "incomplete", "content": []}]},
        {"output": [{"type": "message", "role": "assistant", "status": "completed", "content": "x"}]},
    ):
        bad = _native()
        bad.update(change)
        with pytest.raises(InvocationPortError, match="unsupported_provider_output"):
            decode_openai_responses_response(json.dumps(bad).encode(), _prepared())


def test_openai_request_size_is_enforced_before_secret_lookup_or_network() -> None:
    original = _prepared()
    huge = "x" * 1_048_577
    request = InferenceRequest(
        original.request.target, (Message(Role.USER, Content((TextContent(huge),))),),
    )
    oversized = replace(original, request=request)
    contacted: list[httpx.Request] = []
    adapter = OpenAIResponsesAdapter(
        _CONFIG, _resolver(), allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda req: (contacted.append(req) or _response()),
        ),
    )
    with pytest.raises(InvocationPortError, match="request_too_large"):
        adapter.invoke(oversized)
    assert contacted == []


def test_openai_invalid_content_type_prevents_payload_deserialization() -> None:
    service, request = _service(httpx.MockTransport(
        lambda _: httpx.Response(
            200, content=b'{"secret":"HIDDEN"}',
            headers={"content-type": "text/html"},
        ),
    ))
    run = service.invoke(request).run
    assert run.failure is not None
    assert run.failure.code == "provider_protocol_error"


def test_openai_async_missing_credential_is_no_network_error() -> None:
    prepared = _prepared()
    seen: list[httpx.Request] = []
    missing = EnvCredentialResolver({_REF: "OPENAI_API_KEY"}, environ={})
    adapter = AsyncOpenAIResponsesAdapter(
        _CONFIG, missing, allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda req: (seen.append(req) or _response()),
        ),
    )
    with pytest.raises(InvocationPortError, match="credential_unavailable"):
        asyncio.run(adapter.ainvoke(prepared))
    assert seen == []


@pytest.mark.parametrize("error,code", (
    (httpx.ReadTimeout("SECRET_NATIVE_TIMEOUT"), "provider_timeout"),
    (httpx.ConnectError("SECRET_NATIVE_CONNECT"), "connection_failure"),
    (httpx.RemoteProtocolError("SECRET_NATIVE_HTTP"), "provider_protocol_error"),
    (TimeoutError("SECRET_NATIVE_TIMER"), "provider_timeout"),
))
def test_openai_async_errors_sanitized(error: Exception, code: str) -> None:
    prepared = _prepared()

    async def fail(_: httpx.Request) -> httpx.Response:
        raise error

    adapter = AsyncOpenAIResponsesAdapter(
        _CONFIG, _resolver(), allow_live=True,
        _test_transport=httpx.MockTransport(fail),
    )
    with pytest.raises(InvocationPortError, match=code) as exc:
        asyncio.run(adapter.ainvoke(prepared))
    assert "SECRET_NATIVE" not in str(exc.value)


def test_openai_async_rejects_oversized_and_non_json_responses() -> None:
    prepared = _prepared()
    for response, code in (
        (httpx.Response(200, content=b"x" * 2_097_153,
                        headers={"content-type": "application/json"}), "response_too_large"),
        (httpx.Response(200, content=b"invalid",
                        headers={"content-type": "text/html"}), "provider_protocol_error"),
        (_response(status=429), "rate_limited"),
    ):
        adapter = AsyncOpenAIResponsesAdapter(
            _CONFIG, _resolver(), allow_live=True,
            _test_transport=httpx.MockTransport(lambda _, expected=response: expected),
        )
        with pytest.raises(InvocationPortError, match=code):
            asyncio.run(adapter.ainvoke(prepared))


def test_openai_async_request_expiry_does_not_contact_mock() -> None:
    original = _prepared()
    expired = replace(
        original, context=replace(
            original.context, deadline=datetime(2000, 1, 1, tzinfo=UTC),
        ),
    )
    seen: list[object] = []
    adapter = AsyncOpenAIResponsesAdapter(
        _CONFIG, _resolver(), allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda req: (seen.append(req) or _response()),
        ),
    )
    with pytest.raises(InvocationPortError, match="provider_timeout"):
        asyncio.run(adapter.ainvoke(expired))
    assert not seen
