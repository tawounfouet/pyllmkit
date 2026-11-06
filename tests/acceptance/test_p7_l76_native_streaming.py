"""P7-AC-041..048: six true HTTP streaming profiles through MockTransport only.

Frames are *incremental wire bytes*; no real provider, secrets or billing.
"""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime

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
    AsyncStreamingPort,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamStatus,
    StreamingPort,
    TextDelta,
    consume_async_stream,
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
    assert isinstance(sync_service, StreamingPort)
    assert isinstance(async_service, AsyncStreamingPort)
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
    streaming, _, request, _, _, _ = service("openai")
    _, _ = streaming, snapshot
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
    _, async_service, request, _ = service("anthropic")
    session = async_service.open_astream(request, None)
    # Anthropic requires max_tokens snapshot, so create an explicit session.
    _, async_service, request, snap = service("anthropic")
    session = async_service.open_astream(request, snap)

    async def run() -> None:
        stream = aiter(session)
        assert isinstance(await anext(stream), ResponseStarted)
        assert isinstance(await anext(stream), TextDelta)
        await stream.aclose()

    asyncio.run(run())
