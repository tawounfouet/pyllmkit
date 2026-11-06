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
