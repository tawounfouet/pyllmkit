"""P7-AC-017..024: no real Ollama/network in default CI; MockTransport only."""

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
    AsyncOllamaAdapter,
    FakeInferenceAdapter,
    OllamaAdapter,
    ProviderConnectionConfig,
    CredentialRef,
    RegisteredAsyncInferencePort,
    RegisteredInferencePort,
)
from pyllmkit.adapters.inference.ollama_mapping import (
    decode_ollama_response,
    encode_ollama_request,
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

_CONN = ProviderConnectionConfig.ollama_local()
_TEXT = frozenset((Modality("text"),))


def _fixture(
    *,
    messages: tuple[Message, ...] | None = None,
    generation_config: GenerationConfig | None = None,
) -> tuple[InMemoryCatalog, DeploymentId, InferenceRequest]:
    catalog = InMemoryCatalog()
    modalities = ModalitySet(_TEXT, _TEXT)
    model = ModelId("m")
    dep_id = DeploymentId("local")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("demo")), modalities=modalities,
    ))
    catalog.deployments.register(Deployment(
        dep_id, model, status=DeploymentStatus.AVAILABLE,
        runtime="ollama", modalities=modalities,
    ))
    if messages is None:
        messages = (Message(Role.USER, Content((TextContent("Hello Ollama"),))),)
    return catalog, dep_id, InferenceRequest(
        DeploymentTarget(dep_id), messages, generation_config,
    )


def _prepared(
    *,
    messages: tuple[Message, ...] | None = None,
    generation_config: GenerationConfig | None = None,
    snapshot: GenerationSupportSnapshot | None = None,
):  # type: ignore[no-untyped-def]
    catalog, dep_id, request = _fixture(
        messages=messages, generation_config=generation_config,
    )
    fake = FakeInferenceAdapter()
    svc = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        fake, {dep_id: "llama3.2:1b"},
    )
    outcome = svc.invoke(request, snapshot)
    assert outcome.run.state is InferenceRunState.COMPLETED
    assert len(fake.calls) == 1
    return fake.calls[0]


def _native(
    text: str = "bonjour",
    *,
    done_reason: str | None = "stop",
    prompt_count: int | None = 5,
    output_count: int | None = 2,
) -> dict[str, object]:
    result: dict[str, object] = {
        "model": "llama3.2:1b",
        "done": True,
        "message": {"role": "assistant", "content": text},
    }
    if done_reason is not None:
        result["done_reason"] = done_reason
    if prompt_count is not None:
        result["prompt_eval_count"] = prompt_count
    if output_count is not None:
        result["eval_count"] = output_count
    return result


def _reply(
    data: dict[str, object] | None = None,
    *,
    status: int = 200,
    content_type: str = "application/json",
) -> httpx.Response:
    return httpx.Response(
        status,
        json=_native() if data is None else data,
        headers={"content-type": content_type},
    )


def _service(
    transport: httpx.MockTransport,
    *,
    allow_live: bool = True,
) -> tuple[InferenceService, InferenceRequest]:
    catalog, dep_id, request = _fixture()
    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"), _CONN,
        sync_factory=lambda config: OllamaAdapter(
            config, allow_live=allow_live, _test_transport=transport,
        ),
    ))
    svc = InferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredInferencePort(registry), {dep_id: "llama3.2:1b"},
    )
    return svc, request


def test_p7_ac017_live_is_disabled_by_default_without_contact() -> None:
    contacted = []

    def fail_if_contacted(request: httpx.Request) -> httpx.Response:
        contacted.append(request)
        return _reply()

    service, request = _service(httpx.MockTransport(fail_if_contacted), allow_live=False)
    result = service.invoke(request)
    assert result.run.state is InferenceRunState.FAILED
    assert result.run.failure is not None
    assert result.run.failure.code == "live_authorization_required"
    assert contacted == []


def test_p7_ac018_sync_ollama_first_invocation_is_mocked_not_live() -> None:
    requests: list[httpx.Request] = []

    def responder(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        assert req.method == "POST"
        assert str(req.url) == "http://127.0.0.1:11434/api/chat"
        assert req.headers["content-type"] == "application/json"
        payload = json.loads(req.content)
        assert payload == {
            "model": "llama3.2:1b",
            "messages": [{"role": "user", "content": "Hello Ollama"}],
            "stream": False,
            "think": False,
        }
        return _reply()

    svc, request = _service(httpx.MockTransport(responder))
    result = svc.invoke(request)
    assert len(requests) == 1
    assert result.run.state is InferenceRunState.COMPLETED
    assert result.response is not None
    assert result.response.run_id == result.run.run_id
    assert result.response.output.text == "bonjour"
    assert result.response.finish_reason is not None
    assert result.response.finish_reason.code is FinishReasonCode.STOP
    assert result.response.usage is not None
    assert result.response.usage.input_tokens == 5
    assert result.response.usage.output_tokens == 2
    assert result.response.usage.total_tokens is None


def test_p7_ac019_role_mapping_preserves_order_and_rejects_unmapped_roles() -> None:
    msgs = (
        Message(Role.SYSTEM, Content((TextContent("Answer briefly"),))),
        Message(Role.USER, Content((TextContent("Bonjour"),))),
        Message(Role.ASSISTANT, Content((TextContent("Salut"),))),
    )
    prepared = _prepared(messages=msgs)
    payload = json.loads(encode_ollama_request(prepared))
    assert [m["role"] for m in payload["messages"]] == [
        "system", "user", "assistant",
    ]
    assert [m["content"] for m in payload["messages"]] == [
        "Answer briefly", "Bonjour", "Salut",
    ]
    for role in (Role.DEVELOPER, Role.TOOL):
        p = _prepared(messages=(Message(role, Content((TextContent("x"),))),))
        with pytest.raises(InvocationPortError, match="unsupported_message_role"):
            encode_ollama_request(p)
    two = _prepared(messages=(Message(
        Role.USER, Content((TextContent("one"), TextContent("two"))),
    ),))
    with pytest.raises(InvocationPortError, match="unsupported_content_structure"):
        encode_ollama_request(two)


def test_p7_ac020_generation_options_are_explicit_and_never_dropped() -> None:
    config = GenerationConfig(
        temperature=0.0, top_p=0.9, top_k=20, max_output_tokens=16,
        seed=3, stop_sequences=("\\n",),
    )
    _, _, req = _fixture(generation_config=config)
    parameters = (
        "temperature", "top_p", "top_k", "max_output_tokens", "seed",
        "stop_sequences",
    )
    snap = GenerationSupportSnapshot(
        req.target,
        tuple(ParameterSupport(k, CapabilitySupport(SupportLevel.NATIVE)) for k in parameters),
    )
    prepared = _prepared(generation_config=config, snapshot=snap)
    payload = json.loads(encode_ollama_request(prepared))
    assert payload["options"] == {
        "temperature": 0.0, "top_p": 0.9, "top_k": 20,
        "num_predict": 16, "seed": 3, "stop": ["\\n"],
    }
    incompatible = GenerationConfig(presence_penalty=0.2)
    _, _, original = _fixture(generation_config=incompatible)
    native = GenerationSupportSnapshot(
        original.target,
        (ParameterSupport("presence_penalty", CapabilitySupport(SupportLevel.NATIVE)),),
    )
    prepared = _prepared(generation_config=incompatible, snapshot=native)
    with pytest.raises(InvocationPortError, match="unsupported_generation_parameter"):
        encode_ollama_request(prepared)


@pytest.mark.parametrize("body,code", [
    ({"done": False, "message": {"role": "assistant", "content": "partial"}}, "provider_protocol_error"),
    ({"done": True, "message": {"role": "tool", "content": "hi"}}, "provider_protocol_error"),
    ({"done": True, "message": {"role": "assistant", "content": 7}}, "provider_protocol_error"),
    ({"done": True, "message": {"role": "assistant", "content": "x", "tool_calls": [{"function": "x"}]}}, "unsupported_provider_output"),
    ({"done": True, "message": {"role": "assistant", "content": "x", "thinking": "PRIVATE"}}, "unsupported_provider_output"),
    ({"done": True, "message": {"role": "assistant", "content": "x", "images": ["x"]}}, "unsupported_provider_output"),
    ({"done": True, "message": {"role": "assistant", "content": "x"}, "logprobs": [{"k": "x"}]}, "unsupported_provider_output"),
    ({"done": True, "message": {"role": "assistant", "content": "x"}, "unknown": "x"}, "provider_protocol_error"),
    ({"done": True, "message": {"role": "assistant", "content": "x", "unknown": "x"}}, "provider_protocol_error"),
    ({"done": True, "model": "other", "message": {"role": "assistant", "content": "x"}}, "provider_model_mismatch"),
    ({"done": True, "message": {"role": "assistant", "content": "x"}, "eval_count": -1}, "provider_protocol_error"),
    ({"done": True, "message": {"role": "assistant", "content": "x"}, "eval_count": True}, "provider_protocol_error"),
])
def test_p7_ac021_invalid_or_nontext_native_output_fails_closed(
    body: dict[str, object], code: str,
) -> None:
    prepared = _prepared()
    with pytest.raises(InvocationPortError, match=code):
        decode_ollama_response(json.dumps(body).encode(), prepared)


def test_p7_ac021_partial_usage_and_unknown_reason_remain_unknown() -> None:
    prepared = _prepared()
    raw = _native(done_reason="future_reason", prompt_count=None, output_count=None)
    response = decode_ollama_response(json.dumps(raw).encode(), prepared)
    assert response.usage is None
    assert response.finish_reason is not None
    assert response.finish_reason.code is FinishReasonCode.UNKNOWN
    assert response.finish_reason.native_reason == "future_reason"
    raw["done_reason"] = "malicious\\nSECRET"
    result = decode_ollama_response(json.dumps(raw).encode(), prepared)
    assert result.finish_reason is not None
    assert result.finish_reason.native_reason is None
    raw["done_reason"] = "length"
    result = decode_ollama_response(json.dumps(raw).encode(), prepared)
    assert result.finish_reason is not None
    assert result.finish_reason.code is FinishReasonCode.LENGTH


@pytest.mark.parametrize("status,code", [
    (302, "provider_protocol_error"), (400, "invalid_request"),
    (401, "authentication_failed"), (404, "model_not_found"),
    (429, "rate_limited"), (503, "provider_overloaded"),
])
def test_p7_ac022_native_http_errors_are_sanitized(
    status: int, code: str,
) -> None:
    svc, request = _service(httpx.MockTransport(lambda _: _reply(
        status=status, data={"secret": "TOKEN_123", "message": "bad"},
    )))
    result = svc.invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == code
    assert "TOKEN_123" not in repr(result)
    assert "TOKEN_123" not in str(result.run.failure)


def test_p7_ac022_bad_content_type_and_invalid_json_fail() -> None:
    for response in (
        _reply(content_type="text/html"),
        httpx.Response(200, content=b"broken", headers={"content-type": "application/json"}),
    ):
        svc, request = _service(httpx.MockTransport(lambda _: response))
        outcome = svc.invoke(request)
        assert outcome.run.failure is not None
        assert outcome.run.failure.code == "provider_protocol_error"


def test_p7_ac022_bounded_reply_cannot_consume_unlimited_payload() -> None:
    huge = b"x" * 2_097_153
    svc, request = _service(httpx.MockTransport(lambda _: httpx.Response(
        200, content=huge, headers={"content-type": "application/json"},
    )))
    result = svc.invoke(request)
    assert result.run.failure is not None
    assert result.run.failure.code == "response_too_large"


def test_p7_ac023_async_native_mapping_and_error_parity() -> None:
    catalog, dep_id, request = _fixture()
    seen: list[httpx.Request] = []

    async def response(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return _reply()

    registry = AdapterRegistry()
    registry.register(AdapterRegistration(
        AdapterKey(runtime="ollama"), _CONN,
        async_factory=lambda cfg: AsyncOllamaAdapter(
            cfg, allow_live=True, _test_transport=httpx.MockTransport(response),
        ),
    ))
    svc = AsyncInferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredAsyncInferencePort(registry), {dep_id: "llama3.2:1b"},
    )
    execution = asyncio.run(svc.ainvoke(request))
    assert execution.run.state is InferenceRunState.COMPLETED
    assert execution.response is not None
    assert execution.response.output.text == "bonjour"
    assert len(seen) == 1


def test_p7_ac023_async_http_errors_are_sanitized() -> None:
    catalog, dep_id, request = _fixture()
    reg = AdapterRegistry()
    reg.register(AdapterRegistration(
        AdapterKey(runtime="ollama"), _CONN,
        async_factory=lambda cfg: AsyncOllamaAdapter(
            cfg, allow_live=True, _test_transport=httpx.MockTransport(
                lambda _: _reply(status=429),
            ),
        ),
    ))
    svc = AsyncInferenceService(
        DeploymentResolver(catalog.models, catalog.deployments, catalog.providers),
        RegisteredAsyncInferencePort(reg), {dep_id: "llama3.2:1b"},
    )
    run = asyncio.run(svc.ainvoke(request)).run
    assert run.failure is not None
    assert run.failure.code == "rate_limited"


def test_p7_ac024_expired_deadline_never_attempts_network() -> None:
    prepared = _prepared()
    expired = replace(prepared.context, deadline=datetime(2000, 1, 1, tzinfo=UTC))
    late = replace(prepared, context=expired)
    touched: list[object] = []
    transport = httpx.MockTransport(lambda request: (
        touched.append(request) or _reply()
    ))
    adapter = OllamaAdapter(_CONN, allow_live=True, _test_transport=transport)
    with pytest.raises(InvocationPortError, match="provider_timeout"):
        adapter.invoke(late)
    assert touched == []


def test_p7_ac024_sync_timeout_and_connection_failure_do_not_leak() -> None:
    prepared = _prepared()

    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("SECRET_IN_EXCEPTION")

    def broken(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("SECRET_IN_EXCEPTION")

    for handler, code in ((timeout, "provider_timeout"), (broken, "connection_failure")):
        adapter = OllamaAdapter(
            _CONN, allow_live=True, _test_transport=httpx.MockTransport(handler),
        )
        with pytest.raises(InvocationPortError, match=code) as exc:
            adapter.invoke(prepared)
        assert "SECRET_IN_EXCEPTION" not in str(exc.value)


def test_p7_ac024_unsafe_adapter_flags_rejected_and_no_network_on_import() -> None:
    with pytest.raises(InvocationPortError, match="live_authorization_invalid"):
        OllamaAdapter(_CONN, allow_live="yes")  # type: ignore[arg-type]
    with pytest.raises(InvocationPortError, match="adapter_connection_invalid"):
        OllamaAdapter(ProviderConnectionConfig.openai(CredentialRef("cloud")), allow_live=True)
