"""P7-G6 adversarial regression tests for native stream event safety.

All provider transports stay synthetic. No credentials or live calls.
"""

import asyncio
import json

import httpx
import pytest

from pyllmkit.adapters.inference import NativeProviderStreamingAdapter
from pyllmkit.adapters.inference.native_stream_mapping import NativeStreamDecoder
from pyllmkit.domain.streaming import ResponseCompleted, ResponseFailed

from test_p7_l76_native_streaming import (
    ALIASES,
    PROVIDERS,
    _fresh_decoder,
    _sse,
    service,
    wire,
)


@pytest.mark.parametrize("provider", ("openai", "xai"))
@pytest.mark.parametrize("hidden", (
    {"output": [{"type": "reasoning", "encrypted_content": "PRIVATE"}]},
    {"tools": [{"type": "function", "name": "execute"}]},
    {"store": True},
    {"error": {"message": "SECRET_NATIVE_ERROR"}},
    {"model": "unexpected-model"},
))
def test_responses_progress_rejects_hidden_or_unsafe_state(
    provider: str, hidden: dict[str, object],
) -> None:
    decoder = _fresh_decoder(provider)
    frame = {
        "type": "response.created",
        "response": {"status": "in_progress", **hidden},
    }
    with pytest.raises(Exception, match="provider_protocol_error") as exc:
        decoder.push("response.created", frame)
    assert "PRIVATE" not in str(exc.value)
    assert "SECRET_NATIVE_ERROR" not in str(exc.value)


@pytest.mark.parametrize("provider", ("openai", "xai"))
@pytest.mark.parametrize("hidden", (
    {"encrypted_content": "PRIVATE"},
    {"content": [{"type": "reasoning", "text": "PRIVATE"}]},
    {"content": [{"type": "output_text", "text": "EXTRA"}]},
))
def test_responses_output_item_added_rejects_hidden_content(
    provider: str, hidden: dict[str, object],
) -> None:
    decoder = _fresh_decoder(provider)
    frame = {
        "type": "response.output_item.added",
        "output_index": 0,
        "item": {"type": "message", "role": "assistant", **hidden},
    }
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("response.output_item.added", frame)


@pytest.mark.parametrize("provider", ("openai", "xai"))
def test_responses_output_item_done_must_equal_incremental_text(provider: str) -> None:
    decoder = _fresh_decoder(provider)
    decoder.push("response.output_text.delta", {
        "type": "response.output_text.delta", "output_index": 0,
        "content_index": 0, "delta": "Hello",
    })
    with pytest.raises(Exception, match="provider_stream_mismatch"):
        decoder.push("response.output_item.done", {
            "type": "response.output_item.done",
            "item": {"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "HELLO UNEXPECTED"},
            ]},
        })


@pytest.mark.parametrize("provider", ("openai", "xai"))
@pytest.mark.parametrize("bad", (
    {"output_index": 1},
    {"content_index": 1},
    {"part": {"type": "output_text", "text": "HIDDEN"}},
    {"part": {"type": "output_text", "reasoning": "HIDDEN"}},
))
def test_responses_content_part_add_must_be_zero_index_and_empty(
    provider: str, bad: dict[str, object],
) -> None:
    decoder = _fresh_decoder(provider)
    frame = {
        "type": "response.content_part.added",
        "output_index": 0, "content_index": 0,
        "part": {"type": "output_text", "text": ""},
        **bad,
    }
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("response.content_part.added", frame)


@pytest.mark.parametrize("provider", ("openai", "xai"))
def test_responses_content_part_done_detects_mismatch(provider: str) -> None:
    decoder = _fresh_decoder(provider)
    decoder.push("response.output_text.delta", {
        "type": "response.output_text.delta",
        "output_index": 0, "content_index": 0, "delta": "Hello",
    })
    with pytest.raises(Exception, match="provider_stream_mismatch"):
        decoder.push("response.content_part.done", {
            "type": "response.content_part.done",
            "part": {"type": "output_text", "text": "bye"},
        })


@pytest.mark.parametrize("provider", ("openai", "xai"))
def test_responses_delta_rejects_unrepresented_encrypted_data(provider: str) -> None:
    decoder = _fresh_decoder(provider)
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("response.output_text.delta", {
            "type": "response.output_text.delta",
            "output_index": 0, "content_index": 0, "delta": "Hi",
            "encrypted_content": "PRIVATE",
        })


@pytest.mark.parametrize("hidden", (
    {"error": "SECRET_NATIVE_ERROR"},
    {"message": {
        "role": "assistant", "content": "x", "reasoning": "PRIVATE",
    }},
))
def test_ollama_rejects_hidden_error_or_message_data(hidden: dict[str, object]) -> None:
    decoder = _fresh_decoder("ollama")
    frame = {
        "model": ALIASES["ollama"], "done": False,
        "message": {"role": "assistant", "content": "x"},
        **hidden,
    }
    with pytest.raises(Exception):
        decoder.push("json", frame)


def test_gemini_refuses_error_even_when_text_candidate_is_valid() -> None:
    decoder = _fresh_decoder("google")
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("message", {
            "error": {"message": "PRIVATE"},
            "candidates": [{"content": {
                "role": "model", "parts": [{"text": "Hi"}],
            }}],
        })


def test_mistral_rejects_unrecognized_reasoning_delta() -> None:
    decoder = _fresh_decoder("mistral")
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("message", {
            "object": "chat.completion.chunk", "model": ALIASES["mistral"],
            "choices": [{"index": 0, "finish_reason": None,
                         "delta": {"content": "Hi", "reasoning": "PRIVATE"}}],
        })


def _anthropic_started() -> NativeStreamDecoder:
    decoder = _fresh_decoder("anthropic")
    decoder.push("message_start", {
        "type": "message_start", "message": {
            "type": "message", "role": "assistant",
            "model": ALIASES["anthropic"], "content": [],
        },
    })
    return decoder


def test_anthropic_rejects_payload_in_ping_and_text_block() -> None:
    decoder = _anthropic_started()
    with pytest.raises(Exception, match="provider_protocol_error"):
        decoder.push("ping", {"type": "ping", "thinking": "PRIVATE"})
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("content_block_start", {
            "type": "content_block_start", "index": 0,
            "content_block": {"type": "text", "text": "", "citations": ["private"]},
        })


def test_anthropic_rejects_extra_delta_and_stop_sequence() -> None:
    decoder = _anthropic_started()
    decoder.push("content_block_start", {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "text", "text": ""},
    })
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": "Hi", "thinking": "PRIVATE"},
        })
    decoder = _anthropic_started()
    decoder.push("content_block_start", {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "text", "text": "Hi"},
    })
    decoder.push("content_block_stop", {"type": "content_block_stop", "index": 0})
    with pytest.raises(Exception, match="unsupported_provider_output"):
        decoder.push("message_delta", {
            "type": "message_delta", "delta": {
                "stop_reason": "end_turn", "stop_sequence": "PRIVATE",
            },
        })


@pytest.mark.parametrize("provider", PROVIDERS)
def test_async_truncated_native_wire_fails_safely(provider: str) -> None:
    _, async_service, request, snapshot = service(provider, truncate=True)

    async def collect() -> list[object]:
        return [event async for event in async_service.open_astream(request, snapshot)]

    events = asyncio.run(collect())
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_not_completed"
    assert not any(isinstance(event, ResponseCompleted) for event in events)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_native_frames_after_terminal_fail_without_second_success(provider: str) -> None:
    sync, _, request, snapshot = service(provider)
    session = sync.open_stream(request, snapshot)
    if provider == "ollama":
        extra = json.dumps({
            "message": {"role": "assistant", "content": "UNEXPECTED"},
            "done": False,
        }).encode() + b"\n"
        mime = "application/x-ndjson"
    else:
        extra = _sse(None, {"type": "unexpected", "content": "PRIVATE"}).encode()
        mime = "text/event-stream"
    adapter = NativeProviderStreamingAdapter(
        session.adapter.config,
        session.adapter.credentials,
        allow_live=True,
        _test_transport=httpx.MockTransport(
            lambda _: httpx.Response(200, content=wire(provider) + extra,
                                     headers={"content-type": mime}),
        ),
    )
    events = list(adapter.stream_prepared(session.prepared))
    assert isinstance(events[-1], ResponseFailed)
    assert not any(isinstance(event, ResponseCompleted) for event in events)
    assert "PRIVATE" not in repr(events)
