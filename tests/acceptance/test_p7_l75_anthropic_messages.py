"""P7-AC-033..040: Anthropic Messages with deterministic, zero-network HTTPX mocks."""

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
    AnthropicMessagesAdapter,
    AsyncAnthropicMessagesAdapter,
    CredentialRef,
    EnvCredentialResolver,
    FakeInferenceAdapter,
    ProviderConnectionConfig,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
)
from pyllmkit.adapters.inference.anthropic_messages_mapping import (
    decode_anthropic_messages_response,
    encode_anthropic_messages_request,
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

_REF = CredentialRef("anthropic-test")
_CONFIG = ProviderConnectionConfig.anthropic(_REF)
_SECRET = "sk-ant-SECRET-CANARY"
_MODEL = "claude-test-model"


def _credentials() -> EnvCredentialResolver:
    return EnvCredentialResolver(
        {_REF: "ANTHROPIC_API_KEY"},
        environ={"ANTHROPIC_API_KEY": _SECRET},
    )


def _catalog(
    messages: tuple[Message, ...] | None = None,
    config: GenerationConfig | None = None,
) -> tuple[InMemoryCatalog, DeploymentId, InferenceRequest]:
    catalog = InMemoryCatalog()
    mods = ModalitySet(
        frozenset((Modality("text"),)), frozenset((Modality("text"),)),
    )
    model_id = ModelId("claude-model")
    provider_id = ProviderId("anthropic")
    dep_id = DeploymentId("anthropic-deployment")
    catalog.models.register(Model(
        model_id, ModelIdentity(ModelFamily("claude")), modalities=mods,
    ))
    catalog.providers.register(InferenceProvider(
        provider_id, "Anthropic", modalities=mods,
    ))
    catalog.deployments.register(Deployment(
        dep_id, model_id, provider_id, DeploymentStatus.AVAILABLE,
        modalities=mods, runtime="cloud",
    ))
    if messages is None:
        messages = (Message(Role.USER, Content((TextContent("Bonjour"),))),)
    return catalog, dep_id, InferenceRequest(
        DeploymentTarget(dep_id), messages, config or GenerationConfig(max_output_tokens=64),
    )


def _snapshot(request: InferenceRequest) -> GenerationSupportSnapshot:
    config = request.generation_config
    assert config is not None
    params = (
        "max_output_tokens", "temperature", "top_p", "top_k",
        "stop_sequences", "seed", "presence_penalty", "frequency_penalty",
    )
    declared = tuple(ParameterSupport(name, CapabilitySupport(SupportLevel.NATIVE))
                     for name in params if getattr(config, name) is not None)
    return GenerationSupportSnapshot(request.target, declared)


def _prepared(
    *,
    messages: tuple[Message, ...] | None = None,
    config: GenerationConfig | None = None,
):  # type: ignore[no-untyped-def]
    catalog, dep_id, request = _catalog(messages, config)
    fake = FakeInferenceAdapter()
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        fake, {dep_id: _MODEL},
    )
    run = service.invoke(request, _snapshot(request)).run
    assert run.state is InferenceRunState.COMPLETED
    return fake.calls[0]


def _native(
    text: str = "Salut",
    *,
    stop: str = "end_turn",
    usage: object = "default",
) -> dict[str, object]:
    response: dict[str, object] = {
        "id": "msg_test_001",
        "type": "message",
        "role": "assistant",
        "model": _MODEL,
        "content": [{"type": "text", "text": text, "citations": None}],
        "stop_reason": stop,
        "stop_sequence": None,
    }
    if usage == "default":
        response["usage"] = {
            "input_tokens": 7, "output_tokens": 3,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 2,
        }
    elif usage is not None:
        response["usage"] = usage
    return response


def _http_response(
    body: dict[str, object] | None = None,
    status: int = 200,
    content_type: str = "application/json",
) -> httpx.Response:
    return httpx.Response(
        status, json=_native() if body is None else body,
        headers={"content-type": content_type},
    )


def _service(
    transport: httpx.MockTransport,
    *,
    allow_live: bool = True,
    credentials: EnvCredentialResolver | None = None,
) -> tuple[InferenceService, InferenceRequest]:
    catalog, dep_id, request = _catalog()
    registry = AdapterRegistry()
    resolver = _credentials() if credentials is None else credentials
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("anthropic"), "cloud"), _CONFIG,
        sync_factory=lambda cfg: AnthropicMessagesAdapter(
            cfg, resolver, allow_live=allow_live, _test_transport=transport,
        ),
    ))
    service = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep_id: _MODEL},
    )
    return service, request


def test_p7_ac033_disabled_by_default_without_credential_or_http_access() -> None:
    contacted: list[httpx.Request] = []
    svc, request = _service(
        httpx.MockTransport(lambda req: (contacted.append(req) or _http_response())),
        allow_live=False,
    )
    result = svc.invoke(request, _snapshot(request))
    assert result.run.failure is not None
    assert result.run.failure.code == "live_authorization_required"
    assert contacted == []


def test_p7_ac034_sync_request_and_response_follow_anthropic_wire_contract() -> None:
    calls: list[httpx.Request] = []

    def responder(req: httpx.Request) -> httpx.Response:
        calls.append(req)
        assert req.method == "POST"
        assert str(req.url) == "https://api.anthropic.com/v1/messages"
        assert req.headers["authorization"] == f"Bearer {_SECRET}"
        assert req.headers["anthropic-version"] == "2026-10-21"
        payload = json.loads(req.content)
        assert payload == {
            "model": _MODEL, "max_tokens": 64, "stream": False,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Bonjour"},
            ]}],
        }
        assert "tools" not in payload and "thinking" not in payload
        return _http_response()

    svc, request = _service(httpx.MockTransport(responder))
    result = svc.invoke(request, _snapshot(request))
    assert result.run.state is InferenceRunState.COMPLETED
    assert result.response is not None
    assert result.response.run_id == result.run.run_id
    assert result.response.output.text == "Salut"
    assert result.response.finish_reason is not None
    assert result.response.finish_reason.code is FinishReasonCode.STOP
    assert result.response.finish_reason.native_reason == "end_turn"
    assert result.response.usage is not None
    assert result.response.usage.input_tokens == 7
    assert result.response.usage.output_tokens == 3
    assert result.response.usage.cached_input_tokens == 2
    assert result.response.usage.total_tokens is None
    assert len(calls) == 1
    assert _SECRET not in repr(result)


def test_p7_ac035_single_leading_system_and_alternating_messages() -> None:
    messages = (
        Message(Role.SYSTEM, Content((TextContent("Respond concisely"),))),
        Message(Role.USER, Content((TextContent("One"),))),
        Message(Role.ASSISTANT, Content((TextContent("Two"),))),
        Message(Role.USER, Content((TextContent("Three"),))),
    )
    payload = json.loads(encode_anthropic_messages_request(
        _prepared(messages=messages),
    ))
    assert payload["system"] == [{"type": "text", "text": "Respond concisely"}]
    assert [x["role"] for x in payload["messages"]] == ["user", "assistant", "user"]
    assert [x["content"][0]["text"] for x in payload["messages"]] == [
        "One", "Two", "Three",
    ]
    assert all(x["role"] != "system" for x in payload["messages"])


@pytest.mark.parametrize("roles,code", (
    ((Role.DEVELOPER, Role.USER), "unsupported_message_role"),
    ((Role.TOOL, Role.USER), "unsupported_message_role"),
    ((Role.USER, Role.SYSTEM, Role.USER), "unsupported_message_structure"),
    ((Role.SYSTEM, Role.SYSTEM, Role.USER), "unsupported_message_structure"),
    ((Role.USER, Role.USER), "unsupported_message_structure"),
    ((Role.ASSISTANT, Role.USER), "unsupported_message_structure"),
    ((Role.USER, Role.ASSISTANT), "unsupported_message_structure"),
    ((Role.SYSTEM,), "unsupported_message_structure"),
))
def test_p7_ac035_unrepresentable_roles_or_order_are_rejected(
    roles: tuple[Role, ...], code: str,
) -> None:
    messages = tuple(Message(r, Content((TextContent("msg"),))) for r in roles)
    with pytest.raises(InvocationPortError, match=code):
        encode_anthropic_messages_request(_prepared(messages=messages))


def test_p7_ac035_content_structure_refused_without_silent_joining() -> None:
    messages = (Message(Role.USER, Content((TextContent("a"), TextContent("b")))),)
    with pytest.raises(InvocationPortError, match="unsupported_content_structure"):
        encode_anthropic_messages_request(_prepared(messages=messages))


def test_p7_ac036_max_tokens_is_required_and_parameters_require_native_support() -> None:
    prepared = _prepared()
    no_config = replace(prepared.request, generation_config=None)
    with pytest.raises(InvocationPortError, match="max_tokens_required"):
        encode_anthropic_messages_request(replace(prepared, request=no_config))
    config = GenerationConfig(
        max_output_tokens=128, temperature=0.2, top_p=0.95,
        top_k=20, stop_sequences=("DONE",),
    )
    payload = json.loads(encode_anthropic_messages_request(_prepared(config=config)))
    assert payload["max_tokens"] == 128
    assert payload["temperature"] == 0.2
    assert payload["top_p"] == 0.95
    assert payload["top_k"] == 20
    assert payload["stop_sequences"] == ["DONE"]
    for field, value in (("seed", 2), ("presence_penalty", 0.2), ("frequency_penalty", 0.2)):
        invalid = GenerationConfig(max_output_tokens=64, **{field: value})
        with pytest.raises(InvocationPortError, match="unsupported_generation_parameter"):
            encode_anthropic_messages_request(_prepared(config=invalid))

    # A forged PreparedInvocation must not bypass a native support declaration.
    no_native = replace(prepared, parameter_assessment=replace(
        prepared.parameter_assessment, assessments=(),
    ))
    with pytest.raises(InvocationPortError, match="unknown_generation_parameter"):
        encode_anthropic_messages_request(no_native)


@pytest.mark.parametrize("reason,code", (
    ("end_turn", FinishReasonCode.STOP),
    ("stop_sequence", FinishReasonCode.STOP),
    ("max_tokens", FinishReasonCode.LENGTH),
    ("model_context_window_exceeded", FinishReasonCode.LENGTH),
    ("future_reason", FinishReasonCode.UNKNOWN),
))
def test_p7_ac037_finish_reason_mapping_preserves_native_reason(
    reason: str, code: FinishReasonCode,
) -> None:
    result = decode_anthropic_messages_response(
        json.dumps(_native(stop=reason)).encode(), _prepared(),
    )
    assert result.finish_reason is not None
    assert result.finish_reason.code is code
    assert result.finish_reason.native_reason == reason


@pytest.mark.parametrize("reason,code", (
    ("tool_use", "unsupported_provider_output"),
    ("refusal", "provider_refusal"),
    ("pause_turn", "provider_not_completed"),
))
def test_p7_ac037_tool_refusal_pause_never_claim_completion(
    reason: str, code: str,
) -> None:
    with pytest.raises(InvocationPortError, match=code):
        decode_anthropic_messages_response(
            json.dumps(_native(stop=reason)).encode(), _prepared(),
        )


@pytest.mark.parametrize("content", (
    [],
    [{"type": "thinking", "thinking": "PRIVATE"}],
    [{"type": "tool_use", "name": "unsafe"}],
    [{"type": "text", "text": 7}],
    [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
    [{"type": "text", "text": "a", "citations": [{"url": "secret"}]}],
    [{"type": "text", "text": "a", "unexpected": "private"}],
))
def test_p7_ac037_nontext_and_unmapped_outputs_are_rejected(
    content: list[dict[str, object]],
) -> None:
    response = _native()
    response["content"] = content
    with pytest.raises(InvocationPortError, match="unsupported_provider_output"):
        decode_anthropic_messages_response(json.dumps(response).encode(), _prepared())


def test_p7_ac038_usage_is_partial_and_cache_creation_is_not_discarded() -> None:
    data = _native(usage={"input_tokens": 7})
    first = decode_anthropic_messages_response(json.dumps(data).encode(), _prepared())
    assert first.usage is not None
    assert first.usage.input_tokens == 7
    assert first.usage.total_tokens is None
    assert first.usage.cached_input_tokens is None
    data = _native(usage=None)
    empty = decode_anthropic_messages_response(json.dumps(data).encode(), _prepared())
    assert empty.usage is None
    data["usage"] = {"cache_read_input_tokens": 3}
    cached = decode_anthropic_messages_response(json.dumps(data).encode(), _prepared())
    assert cached.usage is not None
    assert cached.usage.cached_input_tokens == 3
    data["usage"] = {"cache_creation_input_tokens": 2}
    with pytest.raises(InvocationPortError, match="unsupported_provider_usage"):
        decode_anthropic_messages_response(json.dumps(data).encode(), _prepared())


@pytest.mark.parametrize("usage", (
    {"input_tokens": -1},
    {"output_tokens": True},
    {"cache_read_input_tokens": "10"},
    {"cache_creation_input_tokens": -1},
    {"output_tokens_details": {"thinking_tokens": -1}},
    {"output_tokens_details": []},
))
def test_p7_ac038_invalid_native_usage_fails_closed(usage: dict[str, object]) -> None:
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_anthropic_messages_response(
            json.dumps(_native(usage=usage)).encode(), _prepared(),
        )


@pytest.mark.parametrize("status,code", (
    (300, "provider_protocol_error"), (400, "invalid_request"),
    (401, "authentication_failed"), (403, "permission_denied"),
    (404, "model_not_found"), (408, "provider_timeout"),
    (429, "rate_limited"), (500, "provider_overloaded"),
))
def test_p7_ac039_http_status_never_exposes_native_body(
    status: int, code: str,
) -> None:
    svc, request = _service(httpx.MockTransport(
        lambda _: _http_response({"error": {"message": _SECRET}}, status),
    ))
    outcome = svc.invoke(request, _snapshot(request))
    assert outcome.run.failure is not None
    assert outcome.run.failure.code == code
    assert _SECRET not in repr(outcome)


def test_p7_ac039_missing_credential_cannot_trigger_any_network_request() -> None:
    calls: list[httpx.Request] = []
    missing = EnvCredentialResolver({_REF: "ANTHROPIC_API_KEY"}, environ={})
    svc, request = _service(
        httpx.MockTransport(lambda req: (calls.append(req) or _http_response())),
        credentials=missing,
    )
    failed = svc.invoke(request, _snapshot(request))
    assert failed.run.failure is not None
    assert failed.run.failure.code == "credential_unavailable"
    assert calls == []


def test_p7_ac040_async_mock_parity_and_default_off() -> None:
    cat, dep, request = _catalog()
    seen: list[httpx.Request] = []

    async def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return _http_response()

    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(ProviderId("anthropic"), "cloud"), _CONFIG,
        async_factory=lambda cfg: AsyncAnthropicMessagesAdapter(
            cfg, _credentials(), allow_live=True,
            _test_transport=httpx.MockTransport(handler),
        ),
    ))
    service = AsyncInferenceService(
        DeploymentResolver(cat.models, cat.deployments, cat.providers),
        RegisteredAsyncInferencePort(registry), {dep: _MODEL},
    )
    result = asyncio.run(service.ainvoke(request, _snapshot(request)))
    assert result.response is not None
    assert result.response.output.text == "Salut"
    assert result.response.run_id == result.run.run_id
    assert len(seen) == 1
    with pytest.raises(InvocationPortError, match="live_authorization_required"):
        asyncio.run(AsyncAnthropicMessagesAdapter(
            _CONFIG, _credentials(),
        ).ainvoke(_prepared()))


def test_p7_ac040_expired_deadline_no_http_and_max_reply_size() -> None:
    prepared = _prepared()
    expired = replace(prepared, context=replace(
        prepared.context, deadline=datetime(2000, 1, 1, tzinfo=UTC),
    ))
    touched: list[httpx.Request] = []
    adapter = AnthropicMessagesAdapter(
        _CONFIG, _credentials(), allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda req: (touched.append(req) or _http_response()),
        ),
    )
    with pytest.raises(InvocationPortError, match="provider_timeout"):
        adapter.invoke(expired)
    assert touched == []
    huge = httpx.Response(
        200, content=b"x" * 2_097_153,
        headers={"content-type": "application/json"},
    )
    oversized = AnthropicMessagesAdapter(
        _CONFIG, _credentials(), allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: huge),
    )
    with pytest.raises(InvocationPortError, match="response_too_large"):
        oversized.invoke(prepared)


@pytest.mark.parametrize("error,code", (
    (httpx.ReadTimeout("NATIVE-SECRET"), "provider_timeout"),
    (httpx.ConnectError("NATIVE-SECRET"), "connection_failure"),
    (httpx.RemoteProtocolError("NATIVE-SECRET"), "provider_protocol_error"),
))
def test_p7_ac040_native_http_errors_sanitized(
    error: Exception, code: str,
) -> None:
    prepared = _prepared()

    def fail(_: httpx.Request) -> httpx.Response:
        raise error

    adapter = AnthropicMessagesAdapter(
        _CONFIG, _credentials(), allow_live=True,
        _test_transport=httpx.MockTransport(fail),
    )
    with pytest.raises(InvocationPortError, match=code) as exc:
        adapter.invoke(prepared)
    assert "NATIVE-SECRET" not in str(exc.value)
