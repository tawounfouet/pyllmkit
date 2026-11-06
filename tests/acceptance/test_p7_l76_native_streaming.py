"""P7-AC-041..048: six true HTTP streaming profiles through MockTransport only.

Frames are *incremental wire bytes*; no real provider, secrets or billing.
"""

import asyncio
import json

import httpx
import pytest

from pyllmkit.adapters.inference import (
    CredentialRef,
    EnvCredentialResolver,
    NativeProviderStreamingAdapter,
    ProviderConnectionConfig,
    ProviderProfile,
)
from pyllmkit.adapters.inference.native_stream_mapping import (
    NativeStreamDecoder,
    decode_native_json,
)
from pyllmkit.adapters.inference.native_stream_transport import _sse_frames
from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.inference import (
    AsyncStreamingInferenceService,
    InvocationPreconditionError,
    StreamingInferenceService,
)
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    GenerationConfig,
    GenerationSupportSnapshot,
    InferenceRequest,
    ParameterSupport,
)
from pyllmkit.domain.interactions import Content, Message, Role, TextContent
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamStatus,
    TextDelta,
    consume_stream,
)

PROVIDERS = ("ollama", "openai", "anthropic", "google", "xai", "mistral")
ALIASES = {
    "ollama": "llama-synthetic",
    "openai": "gpt-text-test",
    "anthropic": "claude-text-test",
    "google": "gemini-text-test",
    "xai": "grok-text-test",
    "mistral": "mistral-text-test",
}
KEY = "synthetic-not-a-real-credential"


def fixture(provider: str, *, max_tokens: bool = False):  # type: ignore[no-untyped-def]
    catalog = InMemoryCatalog()
    text = frozenset({Modality("text")})
    modes = ModalitySet(text, text)
    model, dep = ModelId("model"), DeploymentId("stream-deployment")
    catalog.models.register(Model(
        model, ModelIdentity(ModelFamily("test")), modalities=modes,
    ))
    if provider == "ollama":
        provider_id, runtime = None, "ollama"
        config = ProviderConnectionConfig.ollama_local()
        resolver = None
    else:
        provider_id, runtime = ProviderId(provider), "cloud"
        catalog.providers.register(InferenceProvider(
            provider_id, provider, modalities=modes,
        ))
        config = getattr(ProviderConnectionConfig, provider)(CredentialRef(f"{provider}-key"))
        ref = config.credential_ref
        assert ref is not None
        resolver = EnvCredentialResolver(
            {ref: "SYNTHETIC_API_KEY"},
            environ={"SYNTHETIC_API_KEY": KEY},
        )
    catalog.deployments.register(Deployment(
        dep, model, provider_id, DeploymentStatus.AVAILABLE,
        runtime=runtime, modalities=modes,
    ))
    generation = GenerationConfig(max_output_tokens=32) if max_tokens else None
    request = InferenceRequest(
        DeploymentTarget(dep),
        (Message(Role.USER, Content((TextContent("hello"),))),),
        generation,
    )
    snapshot = (
        GenerationSupportSnapshot(request.target, (
            ParameterSupport(
                "max_output_tokens", CapabilitySupport(SupportLevel.NATIVE),
            ),
        )) if max_tokens else None
    )
    resolver_port = DeploymentResolver(
        catalog.models, catalog.deployments, catalog.providers,
    )
    return resolver_port, dep, request, snapshot, config, resolver


def _sse(name: str | None, data: object) -> str:
    event = f"event: {name}\n" if name is not None else ""
    return event + "data: " + json.dumps(data, separators=(",", ":")) + "\n\n"


def wire(provider: str, *, truncate: bool = False) -> bytes:
    """Original wire fixtures, including a genuine terminal frame."""
    alias = ALIASES[provider]
    if provider == "ollama":
        chunks = [
            {"model": alias, "message": {"role": "assistant", "content": "He"}, "done": False},
            {"model": alias, "message": {"role": "assistant", "content": "llo"}, "done": False},
        ]
        if not truncate:
            chunks.append({
                "model": alias, "message": {"role": "assistant", "content": ""},
                "done": True, "done_reason": "stop",
                "prompt_eval_count": 3, "eval_count": 2,
            })
        return ("\n".join(json.dumps(obj) for obj in chunks) + "\n").encode()
    if provider in ("openai", "xai"):
        result = {
            "object": "response", "model": alias, "status": "completed",
            "error": None, "incomplete_details": None, "store": False,
            "output": [{
                "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": "Hello", "annotations": []}],
            }],
        }
        if provider == "openai":
            result["usage"] = {"input_tokens": 3, "output_tokens": 2, "total_tokens": 5}
        else:
            result["usage"] = {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
        chunks = [
            _sse("response.created", {
                "type": "response.created", "response": {"status": "in_progress"},
            }),
            _sse("response.output_text.delta", {
                "type": "response.output_text.delta",
                "output_index": 0, "content_index": 0, "delta": "He",
            }),
            _sse("response.output_text.delta", {
                "type": "response.output_text.delta",
                "output_index": 0, "content_index": 0, "delta": "llo",
            }),
            _sse("response.output_text.done", {
                "type": "response.output_text.done",
                "output_index": 0, "content_index": 0, "text": "Hello",
            }),
        ]
        if not truncate:
            chunks.append(_sse("response.completed", {
                "type": "response.completed", "response": result,
            }))
            chunks.append("data: [DONE]\n\n")
        return "".join(chunks).encode()
    if provider == "anthropic":
        chunks = [
            _sse("message_start", {
                "type": "message_start",
                "message": {
                    "type": "message", "role": "assistant", "model": alias,
                    "content": [], "usage": {"input_tokens": 3},
                },
            }),
            _sse("content_block_start", {
                "type": "content_block_start", "index": 0,
                "content_block": {"type": "text", "text": ""},
            }),
            _sse("content_block_delta", {
                "type": "content_block_delta", "index": 0,
                "delta": {"type": "text_delta", "text": "He"},
            }),
            _sse("ping", {"type": "ping"}),
            _sse("content_block_delta", {
                "type": "content_block_delta", "index": 0,
                "delta": {"type": "text_delta", "text": "llo"},
            }),
            _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ]
        if not truncate:
            chunks += [
                _sse("message_delta", {
                    "type": "message_delta", "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 2},
                }),
                _sse("message_stop", {"type": "message_stop"}),
            ]
        return "".join(chunks).encode()
    if provider == "google":
        chunks = [
            _sse(None, {"candidates": [{
                "content": {"role": "model", "parts": [{"text": "He"}]},
            }]}),
            _sse(None, {"candidates": [{
                "content": {"role": "model", "parts": [{"text": "llo"}]},
                **({} if truncate else {"finishReason": "STOP"}),
            }], **({} if truncate else {
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
            })}),
        ]
        return "".join(chunks).encode()
    if provider == "mistral":
        chunks = [
            _sse(None, {
                "object": "chat.completion.chunk", "model": alias,
                "choices": [{"index": 0, "delta": {
                    "role": "assistant", "content": "He",
                }, "finish_reason": None}],
            }),
            _sse(None, {
                "object": "chat.completion.chunk", "model": alias,
                "choices": [{"index": 0, "delta": {
                    "content": "llo",
                }, "finish_reason": None if truncate else "stop"}],
            }),
        ]
        if not truncate:
            chunks.append(_sse(None, {
                "object": "chat.completion.chunk", "model": alias,
                "choices": [], "usage": {
                    "prompt_tokens": 3, "completion_tokens": 2,
                    "total_tokens": 5,
                },
            }))
            chunks.append("data: [DONE]\n\n")
        return "".join(chunks).encode()
    raise AssertionError("unknown fixture")


def transport(provider: str, *, truncate: bool = False) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.method == "POST"
        if provider == "ollama":
            assert str(request.url) == "http://127.0.0.1:11434/api/chat"
            assert payload["think"] is False
            assert payload["stream"] is True
            mime = "application/x-ndjson"
        else:
            assert request.url.host in (
                "api.openai.com", "api.anthropic.com",
                "generativelanguage.googleapis.com", "api.x.ai", "api.mistral.ai",
            )
            assert "authorization" in request.headers or "x-goog-api-key" in request.headers
            if provider == "anthropic":
                assert request.headers["anthropic-version"] == "2026-10-21"
            if provider == "google":
                assert request.url.query == b"alt=sse"
            else:
                assert payload["stream"] is True
            mime = "text/event-stream"
        return httpx.Response(
            200, content=wire(provider, truncate=truncate),
            headers={"content-type": mime},
        )
    return httpx.MockTransport(handle)


def service(provider: str, *, truncate: bool = False, live: bool = True):  # type: ignore[no-untyped-def]
    resolver, dep, req, snapshot, config, creds = fixture(
        provider, max_tokens=provider == "anthropic",
    )
    adapter = NativeProviderStreamingAdapter(
        config, creds, allow_live=live, _test_transport=transport(provider, truncate=truncate),
    )
    bindings = {dep: adapter}
    aliases = {dep: ALIASES[provider]}
    return (
        StreamingInferenceService(resolver, bindings, aliases),
        AsyncStreamingInferenceService(resolver, bindings, aliases),
        req, snapshot,
    )


@pytest.mark.parametrize("provider", PROVIDERS)
def test_p7_ac041_to_046_six_provider_native_sync_stream(provider: str) -> None:
    sync_service, _, request, snapshot = service(provider)
    session = sync_service.open_stream(request, snapshot)
    events = list(session)
    assert isinstance(events[0], ResponseStarted)
    deltas = [event.delta for event in events if isinstance(event, TextDelta)]
    assert deltas == ["He", "llo"]
    assert isinstance(events[-1], ResponseCompleted)
    assert all(event.run_id == session.run_id for event in events)
    assert [event.sequence for event in events] == list(range(len(events)))
    state = consume_stream(type("Memory", (), {
        "run_id": session.run_id, "__iter__": lambda self: iter(events),
    })())
    assert state.status is StreamStatus.COMPLETED
    assert state.text == "Hello"
    assert state.usage is not None
    assert state.usage.input_tokens == 3
    assert state.usage.output_tokens == 2
    assert state.usage_final is True


@pytest.mark.parametrize("provider", PROVIDERS)
def test_p7_ac041_to_046_six_provider_native_async_stream(provider: str) -> None:
    _, async_service, request, snapshot = service(provider)
    session = async_service.open_astream(request, snapshot)

    async def run() -> list[object]:
        return [item async for item in session]

    events = asyncio.run(run())
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[-1], ResponseCompleted)
    assert [event.delta for event in events if isinstance(event, TextDelta)] == [
        "He", "llo",
    ]
    assert all(event.run_id == session.run_id for event in events)
    assert [event.sequence for event in events] == list(range(len(events)))


@pytest.mark.parametrize("provider", PROVIDERS)
def test_p7_ac047_eof_without_terminal_is_failure_not_completed(provider: str) -> None:
    sync_service, _, request, snapshot = service(provider, truncate=True)
    events = list(sync_service.open_stream(request, snapshot))
    assert [event.delta for event in events if isinstance(event, TextDelta)] == [
        "He", "llo",
    ]
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_not_completed"
    assert not any(isinstance(event, ResponseCompleted) for event in events)


def test_p7_ac048_m5_sync_and_async_signatures_are_still_supported() -> None:
    sync_service, async_service, request, _ = service("openai")
    assert callable(sync_service.stream)
    assert callable(async_service.astream)
    events = list(sync_service.stream(request))
    assert isinstance(events[-1], ResponseCompleted)

    async def run() -> list[object]:
        return [event async for event in async_service.astream(request)]

    streamed = asyncio.run(run())
    assert isinstance(streamed[-1], ResponseCompleted)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_p7_ac048_disabled_live_flag_refuses_network(provider: str) -> None:
    sync_service, _, request, snapshot = service(provider, live=False)
    events = list(sync_service.open_stream(request, snapshot))
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "live_authorization_required"


def test_p7_ac048_missing_registered_adapter_fails_closed() -> None:
    resolver, dep, request, _, _, _ = fixture("ollama")
    sync = StreamingInferenceService(
        resolver, {}, {dep: ALIASES["ollama"]},
    )
    with pytest.raises(InvocationPreconditionError, match="streaming_adapter_not_registered"):
        sync.open_stream(request)
    with pytest.raises(TypeError, match="invalid_streaming_adapter_binding"):
        StreamingInferenceService(resolver, {dep: object()}, {dep: ALIASES["ollama"]})


def test_p7_ac048_sse_parser_handles_comments_and_multi_line_payload() -> None:
    lines = iter((": welcome", "event: ping", "data: {", 'data: "type":"ping"}', ""))
    assert list(_sse_frames(lines)) == [("ping", '{\n"type":"ping"}')]
    with pytest.raises(Exception, match="provider_not_completed"):
        list(_sse_frames(iter(("event: ping", 'data: {"type":"ping"}'))))


def test_p7_ac048_adversarial_tool_event_fails_without_completion() -> None:
    _, _, _, snapshot, config, resolver = fixture("openai")
    adapter = NativeProviderStreamingAdapter(
        config, resolver, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            200, content=_sse("response.output_item.added", {
                "type": "response.output_item.added",
                "item": {"type": "function_call", "name": "danger"},
            }).encode(),
            headers={"content-type": "text/event-stream"},
        )),
    )
    streaming, _, request, _ = service("openai")
    _ = snapshot
    prepared = streaming.open_stream(request).prepared
    events = list(adapter.stream_prepared(prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "unsupported_provider_output"


def test_p7_ac048_native_response_mismatch_is_refused() -> None:
    sync, _, request, snapshot = service("openai")
    session = sync.open_stream(request, snapshot)
    decoder = NativeStreamDecoder(ProviderProfile.OPENAI, session.prepared)
    decoder.push("response.output_text.delta", {
        "type": "response.output_text.delta", "output_index": 0,
        "content_index": 0, "delta": "text",
    })
    full = {
        "object": "response", "model": ALIASES["openai"], "status": "completed",
        "output": [{
            "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": "different"}],
        }],
    }
    with pytest.raises(Exception, match="provider_stream_mismatch"):
        decoder.push("response.completed", {
            "type": "response.completed", "response": full,
        })


def test_native_stream_accepts_snapshot_model_alias() -> None:
    sync, _, request, snapshot = service("openai")
    session = sync.open_stream(request, snapshot)
    decoder = NativeStreamDecoder(ProviderProfile.OPENAI, session.prepared)
    # response.created with a dated snapshot matching ALIASES["openai"] ("gpt-text-test-2024-08-06")
    decoder.push("response.created", {
        "type": "response.created",
        "response": {
            "status": "in_progress",
            "model": f"{ALIASES['openai']}-2024-08-06",
        },
    })
    # response.created with an unrelated model is rejected
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("response.created", {
            "type": "response.created",
            "response": {
                "status": "in_progress",
                "model": "unrelated-model",
            },
        })



def test_p7_ac048_duplicate_json_fields_and_excessive_wire_line_rejected() -> None:
    with pytest.raises(Exception, match="provider_protocol_error"):
        decode_native_json('{"type":"ping","type":"ping"}')
    with pytest.raises(Exception, match="provider_protocol_error"):
        decode_native_json("x" * 262_145)


def test_p7_ac048_early_sync_close_does_not_consume_remaining_frames() -> None:
    sync, _, request, _ = service("ollama")
    session = sync.open_stream(request)
    iterator = iter(session)
    assert isinstance(next(iterator), ResponseStarted)
    assert isinstance(next(iterator), TextDelta)
    iterator.close()
    # A closed iterator must not invent or publish ResponseCompleted.


def test_p7_ac048_early_async_close_does_not_consume_remaining_frames() -> None:
    _, async_service, request, snap = service("anthropic")
    session = async_service.open_astream(request, snap)

    async def run() -> None:
        stream = aiter(session)
        assert isinstance(await anext(stream), ResponseStarted)
        assert isinstance(await anext(stream), TextDelta)
        await stream.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_single_use_sync_session_prevents_repeat_network_with_same_run_id(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)
    first = list(session)
    assert isinstance(first[-1], ResponseCompleted)
    with pytest.raises(InvocationPreconditionError, match="stream_session_already_consumed"):
        iter(session)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_single_use_async_session_prevents_repeat_network_with_same_run_id(provider: str) -> None:
    _, async_service, req, snap = service(provider)
    session = async_service.open_astream(req, snap)

    async def twice() -> None:
        first = [event async for event in session]
        assert isinstance(first[-1], ResponseCompleted)
        with pytest.raises(InvocationPreconditionError, match="stream_session_already_consumed"):
            aiter(session)

    asyncio.run(twice())


@pytest.mark.parametrize("provider", PROVIDERS)
def test_wrong_provider_stream_binding_cannot_route_another_deployment(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)
    other = "openai" if provider != "openai" else "anthropic"
    _, _, _, _, config, credentials = fixture(other)
    mismatched = NativeProviderStreamingAdapter(
        config, credentials, allow_live=True,
        _test_transport=transport(other),
    )
    events = list(mismatched.stream_prepared(session.prepared))
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "adapter_connection_invalid"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_provider_non_200_http_status_never_completes_stream(provider: str) -> None:
    sync, _, req, snap = service(provider)
    cfg = sync.open_stream(req, snap).adapter.config
    creds = sync.open_stream(req, snap).adapter.credentials
    mime = "application/x-ndjson" if provider == "ollama" else "text/event-stream"
    adapter = NativeProviderStreamingAdapter(
        cfg, creds, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            429, json={"error": {"message": "SECRET_BODY"}},
            headers={"content-type": mime},
        )),
    )
    events = list(adapter.stream_prepared(sync.open_stream(req, snap).prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "rate_limited"
    assert "SECRET_BODY" not in repr(events)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_wrong_stream_mime_is_not_parsed_as_json_or_sse(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)
    original = session.adapter
    adapter = NativeProviderStreamingAdapter(
        original.config, original.credentials, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            200, content=wire(provider), headers={"content-type": "text/html"},
        )),
    )
    events = list(adapter.stream_prepared(session.prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_protocol_error"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_stream_transport_connection_timeout_and_remote_errors(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)
    for error, code in (
        (httpx.ReadTimeout("SECRET_TLS"), "provider_timeout"),
        (httpx.ConnectError("SECRET_TLS"), "connection_failure"),
        (httpx.RemoteProtocolError("SECRET_TLS"), "provider_protocol_error"),
    ):
        def fail(_: httpx.Request, exception: Exception = error) -> httpx.Response:
            raise exception

        adapter = NativeProviderStreamingAdapter(
            session.adapter.config, session.adapter.credentials, allow_live=True,
            _test_transport=httpx.MockTransport(fail),
        )
        events = list(adapter.stream_prepared(session.prepared))
        assert isinstance(events[-1], ResponseFailed)
        assert events[-1].reason_code == code
        assert "SECRET_TLS" not in repr(events)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_stream_async_failure_codes_are_sanitized(provider: str) -> None:
    _, async_service, req, snap = service(provider)
    prepared_session = async_service.open_astream(req, snap)

    async def fail(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("SECRET_ASYNC")

    adapter = NativeProviderStreamingAdapter(
        prepared_session.adapter.config, prepared_session.adapter.credentials,
        allow_live=True, _test_transport=httpx.MockTransport(fail),
    )

    async def collect() -> list[object]:
        return [event async for event in adapter.astream_prepared(prepared_session.prepared)]

    events = asyncio.run(collect())
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_timeout"
    assert "SECRET_ASYNC" not in repr(events)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_stream_request_rejected_if_deadline_is_past(provider: str) -> None:
    from dataclasses import replace
    from datetime import UTC, datetime

    sync, async_service, req, snap = service(provider)
    prepared = sync.open_stream(req, snap).prepared
    invalid = replace(prepared, context=replace(
        prepared.context, deadline=datetime(2000, 1, 1, tzinfo=UTC),
    ))
    adapter = sync.open_stream(req, snap).adapter
    first = list(adapter.stream_prepared(invalid))
    assert isinstance(first[-1], ResponseFailed)
    assert first[-1].reason_code == "provider_timeout"

    async def collect() -> list[object]:
        return [e async for e in async_service.open_astream(req, snap).adapter.astream_prepared(invalid)]
    second = asyncio.run(collect())
    assert isinstance(second[-1], ResponseFailed)
    assert second[-1].reason_code == "provider_timeout"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_stream_injected_native_unexpected_error_uses_safe_terminal(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)

    def fail(_: httpx.Request) -> httpx.Response:
        raise ValueError("NATIVE-SECRET-UNEXPECTED")

    adapter = NativeProviderStreamingAdapter(
        session.adapter.config, session.adapter.credentials, allow_live=True,
        _test_transport=httpx.MockTransport(fail),
    )
    events = list(adapter.stream_prepared(session.prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "adapter_unexpected_error"
    assert "NATIVE-SECRET" not in repr(events)


@pytest.mark.parametrize("provider", ("openai", "xai", "anthropic", "google", "mistral"))
def test_unknown_sse_event_does_not_disappear_silently(provider: str) -> None:
    sync, _, req, snap = service(provider)
    session = sync.open_stream(req, snap)
    body = _sse("danger.tool_call", {
        "type": "danger.tool_call", "arguments": "SECRET_NATIVE",
    })
    adapter = NativeProviderStreamingAdapter(
        session.adapter.config, session.adapter.credentials, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            200, content=body.encode(), headers={"content-type": "text/event-stream"},
        )),
    )
    events = list(adapter.stream_prepared(session.prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert not any(isinstance(x, ResponseCompleted) for x in events)
    assert "SECRET_NATIVE" not in repr(events)


def test_sse_frame_parser_rejects_unsupported_fields_duplicate_event_and_partial_data() -> None:
    cases = (
        ("retry: 3000", ""),
        ("id: 42", ""),
        ("event: a", "event: b", "data: {}", ""),
        ("data: 1", "event: b", ""),
    )
    for lines in cases:
        with pytest.raises(Exception, match="provider_protocol_error"):
            list(_sse_frames(iter(lines)))
    assert list(_sse_frames(iter((": keep-alive", "")))) == []


def test_stream_line_budgets_and_parser_limits_are_enforced() -> None:
    from pyllmkit.adapters.inference.native_stream_transport import (
        _bounded_lines,
    )

    with pytest.raises(Exception, match="stream_wire_limit"):
        list(_bounded_lines(iter(("x" * 262_145,))))
    with pytest.raises(Exception, match="stream_wire_limit"):
        list(_bounded_lines(iter(("x" * 262_144,) * 49)))


@pytest.mark.parametrize("profile", (
    ProviderProfile.OLLAMA, ProviderProfile.GOOGLE, ProviderProfile.OPENAI,
    ProviderProfile.ANTHROPIC, ProviderProfile.XAI, ProviderProfile.MISTRAL,
))
def test_stream_decoder_rejects_invalid_native_data_and_limit(profile: ProviderProfile) -> None:
    case = profile.value
    _, _, req, snap = service(case)
    sync, _, _, _ = service(case)
    prepared = sync.open_stream(req, snap).prepared
    decoder = NativeStreamDecoder(profile, prepared)
    with pytest.raises(
        Exception, match=(
            "unsupported_provider_output" if profile is ProviderProfile.GOOGLE
            else "provider_protocol_error"
        ),
    ):
        decoder.push("json", {"unexpected": "message"})
    with pytest.raises(Exception, match="stream_event_limit"):
        decoder._events = 100_000
        decoder.push("ignored", {})
    with pytest.raises(Exception, match="stream_text_limit"):
        decoder._append("x" * (1_048_576 + 1))


def test_response_decoder_rejects_duplicate_done_marker_and_missing_complete() -> None:
    sync, _, req, snap = service("mistral")
    decoder = NativeStreamDecoder(ProviderProfile.MISTRAL, sync.open_stream(req, snap).prepared)
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.finish()
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.marker("[DONE]")
    decoder._done_marker = False
    decoder._mistral_reason = "stop"
    decoder._chunks.append("Hello")
    decoder.marker("[DONE]")
    assert decoder.finish().output.text == "Hello"
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.marker("[DONE]")


def test_response_decoders_reject_nontext_tool_and_hidden_state() -> None:
    sync, _, req, snap = service("ollama")
    decoder = NativeStreamDecoder(ProviderProfile.OLLAMA, sync.open_stream(req, snap).prepared)
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("json", {
            "model": ALIASES["ollama"], "done": False,
            "message": {"role": "assistant", "content": "x", "tool_calls": [{"name": "run"}]},
        })
    sync, _, req, snap = service("anthropic")
    decoder = NativeStreamDecoder(ProviderProfile.ANTHROPIC, sync.open_stream(req, snap).prepared)
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "PRIVATE"},
        })
    decoder.push("message_start", {
        "type": "message_start", "message": {
            "type": "message", "role": "assistant", "model": ALIASES["anthropic"],
            "content": [],
        },
    })
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("content_block_start", {
            "type": "content_block_start", "index": 0,
            "content_block": {"type": "thinking", "thinking": "PRIVATE"},
        })


def test_stream_mistral_requires_done_after_native_finish() -> None:
    sync, _, req, snap = service("mistral")
    prepared = sync.open_stream(req, snap).prepared
    decoder = NativeStreamDecoder(ProviderProfile.MISTRAL, prepared)
    for line in wire("mistral").decode().splitlines():
        if line.startswith("data: "):
            raw = line[6:]
            if raw == "[DONE]":
                break
            decoder.push("message", json.loads(raw))
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.finish()


def test_stream_response_output_rejects_encrypted_reasoning_before_completion() -> None:
    sync, _, req, snap = service("xai")
    prepared = sync.open_stream(req, snap).prepared
    decoder = NativeStreamDecoder(ProviderProfile.XAI, prepared)
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("response.output_item.added", {
            "type": "response.output_item.added",
            "item": {"type": "reasoning", "encrypted_content": "SECRET"},
        })

def _fresh_decoder(name: str) -> NativeStreamDecoder:
    sync, _, request, support = service(name)
    return NativeStreamDecoder(
        ProviderProfile(name), sync.open_stream(request, support).prepared,
    )


@pytest.mark.parametrize("name", ("openai", "xai"))
@pytest.mark.parametrize("kind", (
    "response.created", "response.in_progress",
    "response.output_item.added", "response.output_item.done",
    "response.content_part.added", "response.content_part.done",
))
def test_responses_known_nontext_lifecycle_frames_are_validated(
    name: str, kind: str,
) -> None:
    decoder = _fresh_decoder(name)
    body: dict[str, object] = {"type": kind}
    if kind in ("response.created", "response.in_progress"):
        body["response"] = {"status": "in_progress"}
    elif kind in ("response.output_item.added", "response.output_item.done"):
        body["item"] = {"type": "message", "role": "assistant"}
    else:
        body["part"] = {"type": "output_text", "annotations": []}
    assert decoder.push(kind, body) == ""
    assert decoder._completed is False


@pytest.mark.parametrize("name", ("openai", "xai"))
def test_responses_incremental_text_done_consistency(name: str) -> None:
    decoder = _fresh_decoder(name)
    assert decoder.push("response.output_text.delta", {
        "type": "response.output_text.delta",
        "output_index": 0, "content_index": 0, "delta": "Hello",
    }) == "Hello"
    assert decoder.push("response.output_text.done", {
        "type": "response.output_text.done",
        "output_index": 0, "content_index": 0, "text": "Hello",
    }) == ""
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.finish()


def test_native_text_limit_and_reassembly_are_bounded_in_bytes() -> None:
    decoder = _fresh_decoder("ollama")
    assert decoder._append("é") == "é"
    assert decoder._text() == "é"
    assert decoder._text_bytes == 2
    decoder._text_bytes = 8 * 1024 * 1024
    with pytest.raises(Exception, match="stream_text_limit"):
        decoder._append("x")
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder._append(None)  # type: ignore[arg-type]


@pytest.mark.parametrize("kind,frame,code", (
    ("content_block_start", {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "text", "text": "x"},
    }, "provider_protocol_error"),
    ("ping", {"type": "pong"}, "provider_protocol_error"),
    ("error", {"type": "error", "error": {"message": "SECRET"}}, "provider_protocol_error"),
))
def test_anthropic_stream_start_phase_fail_closed(
    kind: str, frame: dict[str, object], code: str,
) -> None:
    with pytest.raises(Exception, match=code):
        _fresh_decoder("anthropic").push(kind, frame)


def test_anthropic_stream_uses_native_initial_text_and_cumulative_usage() -> None:
    decoder = _fresh_decoder("anthropic")
    assert decoder.push("message_start", {
        "type": "message_start", "message": {
            "type": "message", "role": "assistant",
            "model": ALIASES["anthropic"], "content": [],
            "usage": {"input_tokens": 5},
        },
    }) == ""
    assert decoder.push("ping", {"type": "ping"}) == ""
    assert decoder.push("content_block_start", {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "text", "text": "Hello"},
    }) == "Hello"
    assert decoder.push("content_block_stop", {
        "type": "content_block_stop", "index": 0,
    }) == ""
    assert decoder.push("message_delta", {
        "type": "message_delta", "delta": {
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "stop_details": None,
            "container": None,
        },
        "usage": {"output_tokens": 4},
    }) == ""
    assert decoder.push("message_stop", {"type": "message_stop"}) == ""
    response = decoder.finish()
    assert response.output.text == "Hello"
    assert response.usage is not None
    assert response.usage.input_tokens == 5
    assert response.usage.output_tokens == 4
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("ping", {"type": "ping"})


def test_mistral_stream_rejects_missing_usage_after_end() -> None:
    decoder = _fresh_decoder("mistral")
    base = {
        "object": "chat.completion.chunk",
        "model": ALIASES["mistral"],
    }
    assert decoder.push("message", {
        **base, "choices": [{"index": 0, "delta": {"content": "Hi"}, "finish_reason": "stop"}],
    }) == "Hi"
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {**base, "choices": [], "usage": None})


def test_mistral_stream_rejects_second_usage_and_delta_after_reason() -> None:
    decoder = _fresh_decoder("mistral")
    base = {"object": "chat.completion.chunk", "model": ALIASES["mistral"]}
    decoder.push("message", {
        **base, "choices": [{
            "index": 0, "delta": {"content": "Hi"}, "finish_reason": "stop",
        }],
    })
    decoder.push("message", {**base, "choices": [], "usage": {"prompt_tokens": 1}})
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {**base, "choices": [], "usage": {"prompt_tokens": 1}})
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {**base, "choices": [{
            "index": 0, "delta": {"content": "after"},
        }]})


@pytest.mark.parametrize("name", ("ollama", "openai", "anthropic", "google", "xai", "mistral"))
def test_native_stream_request_never_reuses_completed_decoder(name: str) -> None:
    decoder = _fresh_decoder(name)
    decoder._completed = True
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("irrelevant", {})
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.finish()


def test_transport_sync_http_stream_closes_on_early_consumer_break() -> None:
    class Tracked(httpx.SyncByteStream):
        def __init__(self) -> None:
            self.closed = False

        def __iter__(self):  # type: ignore[no-untyped-def]
            yield wire("ollama")
            raise AssertionError("body must not be consumed after early close")

        def close(self) -> None:
            self.closed = True

    tracked = Tracked()
    sync, _, request, snapshot = service("ollama")
    source = sync.open_stream(request, snapshot)
    adapter = NativeProviderStreamingAdapter(
        source.adapter.config,
        source.adapter.credentials,
        allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, stream=tracked,
                headers={"content-type": "application/x-ndjson"},
            ),
        ),
    )
    events = adapter.stream_prepared(source.prepared)
    assert isinstance(next(events), ResponseStarted)
    assert isinstance(next(events), TextDelta)
    events.close()
    assert tracked.closed is True


def test_transport_async_http_stream_closes_on_early_consumer_break() -> None:
    class Tracked(httpx.AsyncByteStream):
        def __init__(self) -> None:
            self.closed = False

        async def __aiter__(self):  # type: ignore[no-untyped-def]
            yield wire("anthropic")
            raise AssertionError("body must not be consumed after early close")

        async def aclose(self) -> None:
            self.closed = True

    tracked = Tracked()
    _, service_async, request, snapshot = service("anthropic")
    session = service_async.open_astream(request, snapshot)
    adapter = NativeProviderStreamingAdapter(
        session.adapter.config,
        session.adapter.credentials,
        allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, stream=tracked,
                headers={"content-type": "text/event-stream"},
            ),
        ),
    )

    async def close() -> None:
        events = adapter.astream_prepared(session.prepared)
        assert isinstance(await anext(events), ResponseStarted)
        assert isinstance(await anext(events), TextDelta)
        await events.aclose()

    asyncio.run(close())
    assert tracked.closed is True

@pytest.mark.parametrize("name", ("openai", "xai", "mistral"))
def test_native_done_marker_not_allowed_before_provider_terminal(name: str) -> None:
    decoder = _fresh_decoder(name)
    with pytest.raises(Exception, match="provider_not_completed"):
        decoder.marker("[DONE]")
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.marker("[DONE]")


@pytest.mark.parametrize("name", ("ollama", "google", "anthropic"))
def test_native_done_marker_not_supported_on_non_done_protocols(name: str) -> None:
    decoder = _fresh_decoder(name)
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.marker("[DONE]")


def test_unknown_profile_is_not_implicitly_dispatched() -> None:
    decoder = _fresh_decoder("openai")
    decoder.profile = "not_a_provider"  # type: ignore[assignment]
    with pytest.raises(Exception, match="adapter_connection_invalid"):
        decoder.push("ignored", {})


def test_native_decoder_rejects_duplicate_finalization() -> None:
    decoder = _fresh_decoder("ollama")
    decoder.push("json", {
        "message": {"role": "assistant", "content": "Hello"},
        "done": True, "done_reason": "stop",
    })
    result = decoder.finish()
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder._finalize(result)


def test_native_decoder_fails_if_final_assembled_text_differs() -> None:
    decoder = _fresh_decoder("ollama")
    decoder.push("json", {
        "message": {"role": "assistant", "content": "A"},
        "done": True, "done_reason": "stop",
    })
    from pyllmkit.domain.inference import InferenceResponse, TextOutput

    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("json", {
            "message": {"role": "assistant", "content": "B"}, "done": False,
        })
    other = InferenceResponse(decoder.prepared.context.run_id, TextOutput("B"))
    decoder._completed = False
    with pytest.raises(Exception, match="provider_stream_mismatch"):
        decoder._finalize(other)


@pytest.mark.parametrize("name", ("openai", "xai"))
def test_responses_completion_without_matching_delta_is_rejected(name: str) -> None:
    decoder = _fresh_decoder(name)
    body = {
        "object": "response",
        "status": "completed", "model": ALIASES[name], "store": False,
        "output": [{
            "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": "UNSEEN"}],
        }],
    }
    with pytest.raises(Exception, match="provider_stream_mismatch"):
        decoder.push("response.completed", {
            "type": "response.completed", "response": body,
        })


def test_native_json_bad_shape_and_unsupported_encoding_rejected() -> None:
    for body in ('[]', 'null', 'true', '"word"', '123', 'x' * 262_145):
        with pytest.raises(Exception, match="provider_protocol_error"):
            decode_native_json(body)


def test_gemini_safety_feedback_without_text_is_rejected() -> None:
    decoder = _fresh_decoder("google")
    with pytest.raises(Exception, match="provider_content_filtered"):
        decoder.push("message", {
            "promptFeedback": {"blockReason": "SAFETY"}, "candidates": [],
        })


def test_gemini_invalid_native_part_type_rejected() -> None:
    decoder = _fresh_decoder("google")
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {
            "candidates": [{"content": {
                "role": "model", "parts": [{"text": 3}],
            }}],
        })


def test_anthropic_event_error_and_future_event_rejected_after_start() -> None:
    def start() -> NativeStreamDecoder:
        decoder = _fresh_decoder("anthropic")
        decoder.push("message_start", {
            "type": "message_start",
            "message": {
                "type": "message", "role": "assistant",
                "model": ALIASES["anthropic"], "content": [],
            },
        })
        return decoder

    with pytest.raises(Exception, match="provider_protocol_error"):
        start().push("error", {
            "type": "error", "error": {"message": "PRIVATE_DETAIL"},
        })
    with pytest.raises(Exception, match="unsupported_provider_output"):
        start().push("message.future", {"type": "message.future"})


def test_anthropic_malformed_usage_is_rejected_without_leaks() -> None:
    decoder = _fresh_decoder("anthropic")
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message_start", {
            "type": "message_start",
            "message": {
                "type": "message", "role": "assistant",
                "model": ALIASES["anthropic"], "content": [],
                "usage": ["invalid"],
            },
        })


def test_mistral_usage_can_arrive_in_final_choice_chunk() -> None:
    decoder = _fresh_decoder("mistral")
    assert decoder.push("message", {
        "object": "chat.completion.chunk", "model": ALIASES["mistral"],
        "choices": [{
            "index": 0, "delta": {"role": "assistant", "content": "Hi"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
    }) == "Hi"
    decoder.marker("[DONE]")
    assert decoder.finish().usage is not None
    assert decoder.finish().usage.input_tokens == 1


def test_mistral_usage_without_completed_reason_is_invalid() -> None:
    decoder = _fresh_decoder("mistral")
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {
            "object": "chat.completion.chunk", "model": ALIASES["mistral"],
            "choices": [], "usage": {"prompt_tokens": 3},
        })


def test_native_stream_http_headers_do_not_expose_basic_auth_or_proxy() -> None:
    from pyllmkit.adapters.inference.native_stream_transport import (
        _response_header,
        _stream_headers,
    )

    assert _stream_headers(ProviderProfile.GOOGLE, "fake")["x-goog-api-key"] == "fake"
    assert _stream_headers(ProviderProfile.MISTRAL, "fake")["Authorization"] == "Bearer fake"
    assert _stream_headers(ProviderProfile.ANTHROPIC, "fake")["anthropic-version"] == (
        "2026-10-21"
    )
    assert "Authorization" not in _stream_headers(ProviderProfile.OLLAMA, None)
    with pytest.raises(Exception, match="credential_unavailable"):
        _stream_headers(ProviderProfile.OPENAI, None)
    with pytest.raises(Exception, match="provider_protocol_error"):
        _response_header(ProviderProfile.OPENAI, 200, "text/html")
    with pytest.raises(Exception, match="rate_limited"):
        _response_header(ProviderProfile.OPENAI, 429, "text/event-stream")


def test_streaming_async_service_validates_registered_port_and_missing_binding() -> None:
    resolver, dep, req, _, _, _ = fixture("ollama")
    with pytest.raises(TypeError, match="invalid_async_streaming_adapter_binding"):
        AsyncStreamingInferenceService(resolver, {dep: object()}, {dep: "llama"})
    service_async = AsyncStreamingInferenceService(resolver, {}, {dep: "llama"})
    with pytest.raises(InvocationPreconditionError, match="streaming_adapter_not_registered"):
        service_async.open_astream(req)


def test_m5_asynchronous_session_is_correlated_and_cannot_be_reused_after_close() -> None:
    _, service_async, request, snapshot = service("openai")
    session = service_async.open_astream(request, snapshot)

    async def close_early() -> None:
        iterator = aiter(session)
        assert isinstance(await anext(iterator), ResponseStarted)
        await iterator.aclose()
        with pytest.raises(InvocationPreconditionError, match="stream_session_already_consumed"):
            aiter(session)

    asyncio.run(close_early())
