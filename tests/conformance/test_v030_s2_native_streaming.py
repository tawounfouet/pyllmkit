"""S2 shared native streaming conformance matrix, six provider protocols.

The test executes P7's native streaming adapter against local MockTransport
using self-contained synthetic protocol fixtures. No HTTP connection,
credential or billable inference is created.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from pyllmkit.adapters.inference import NativeProviderStreamingAdapter
from pyllmkit.application.inference import AsyncStreamingSession, StreamingSession
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamEvent,
    TextDelta,
    UsageUpdated,
)
from tests.conformance.providers import PROVIDERS, adapter, prepared
from tests.conformance.stream_fixtures import (
    PROVENANCE,
    malformed_wire,
    stream_mime,
    stream_wire,
)

_OUTCOMES = (
    "complete", "truncated", "malformed", "bad_mime", "rate_limited",
    "post_terminal", "overlong_line",
)


def _stream_adapter(
    provider: str,
    *,
    handler: Callable[[httpx.Request], httpx.Response],
) -> NativeProviderStreamingAdapter:
    """Construct the genuine streaming port through a mock-only connection."""
    transport = httpx.MockTransport(handler)
    normal = adapter(provider, transport=transport, async_mode=False)
    return NativeProviderStreamingAdapter(
        normal.config, getattr(normal, "credentials", None),
        allow_live=True, _test_transport=transport,
    )


def _collect(provider: str, scenario: str, *, async_mode: bool) -> tuple[
    list[StreamEvent], object, list[httpx.Request],
]:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST"
        payload = json.loads(request.content)
        assert isinstance(payload, dict)
        if provider == "google":
            assert request.url.query == b"alt=sse"
        else:
            assert payload["stream"] is True

        if scenario == "rate_limited":
            return httpx.Response(
                429, headers={"content-type": stream_mime(provider)},
                content=b'SYNTHETIC_BODY_MUST_NOT_APPEAR_IN_ERRORS',
            )
        if scenario == "bad_mime":
            return httpx.Response(
                200, headers={"content-type": "text/plain"},
                content=stream_wire(provider),
            )
        if scenario == "malformed":
            body = malformed_wire(provider)
        elif scenario == "overlong_line":
            prefix = b"" if provider == "ollama" else b"data: "
            body = prefix + b"x" * 262_145 + b"\n\n"
        elif scenario == "post_terminal":
            suffix = b"{}\n" if provider == "ollama" else b"data: {}\n\n"
            body = stream_wire(provider) + suffix
        else:
            body = stream_wire(provider, truncate=scenario == "truncated")
        return httpx.Response(
            200, headers={"content-type": stream_mime(provider)}, content=body,
        )

    case = prepared(provider)
    port = _stream_adapter(provider, handler=handler)
    if async_mode:
        session = AsyncStreamingSession(case, port)

        async def run() -> list[StreamEvent]:
            return [event async for event in session]

        events = asyncio.run(run())
    else:
        session = StreamingSession(case, port)
        events = list(session)
    return events, session.run_id, calls


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
@pytest.mark.parametrize("scenario", _OUTCOMES)
def test_native_stream_conformance(
    provider: str, async_mode: bool, scenario: str,
) -> None:
    assert PROVENANCE["source_kind"] == "synthetic"
    assert PROVENANCE["external_network"] is False
    events, run_id, calls = _collect(provider, scenario, async_mode=async_mode)

    assert len(calls) == 1
    assert isinstance(events[0], ResponseStarted)
    assert all(event.run_id == run_id for event in events)
    assert [event.sequence for event in events] == list(range(len(events)))

    if scenario == "complete":
        assert isinstance(events[-1], ResponseCompleted)
        assert [event.delta for event in events if isinstance(event, TextDelta)] == [
            "He", "llo",
        ]
        assert not any(isinstance(event, ResponseFailed) for event in events)
        final_usage = [
            event for event in events
            if isinstance(event, UsageUpdated) and event.is_final
        ]
        assert len(final_usage) == 1
        assert final_usage[0].usage.input_tokens == 3
        assert final_usage[0].usage.output_tokens == 2
    else:
        assert isinstance(events[-1], ResponseFailed)
        assert not any(isinstance(event, ResponseCompleted) for event in events)
        expected = {
            "truncated": "provider_not_completed",
            "malformed": "provider_protocol_error",
            "bad_mime": "provider_protocol_error",
            "rate_limited": "rate_limited",
            "post_terminal": "provider_protocol_error",
            "overlong_line": "stream_wire_limit",
        }
        assert events[-1].reason_code == expected[scenario]
        assert "SYNTHETIC_BODY_MUST_NOT_APPEAR_IN_ERRORS" not in str(events[-1])


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_pre_cancelled_native_session_never_contacts_transport(
    provider: str, async_mode: bool,
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("cancelled session contacted transport")

    case = prepared(provider)
    port = _stream_adapter(provider, handler=handler)
    if async_mode:
        session = AsyncStreamingSession(case, port)
        session.cancel()

        async def collect() -> list[StreamEvent]:
            return [event async for event in session]

        events = asyncio.run(collect())
    else:
        session = StreamingSession(case, port)
        session.cancel()
        events = list(session)

    assert calls == []
    assert len(events) == 2
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[1], ResponseCancelled)
    assert events[1].reason_code == "user_cancelled"
    assert [event.sequence for event in events] == [0, 1]
    assert all(event.run_id == session.run_id for event in events)



@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_ollama_json_content_type_is_explicitly_supported(async_mode: bool) -> None:
    """Ollama native JSONL accepts JSON MIME; SSE providers do not."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, headers={"content-type": "application/json"},
            content=stream_wire("ollama"),
        )

    case = prepared("ollama")
    port = _stream_adapter("ollama", handler=handler)
    if async_mode:
        session = AsyncStreamingSession(case, port)

        async def run() -> list[StreamEvent]:
            return [event async for event in session]

        events = asyncio.run(run())
    else:
        session = StreamingSession(case, port)
        events = list(session)

    assert len(calls) == 1
    assert isinstance(events[-1], ResponseCompleted)
    assert [event.delta for event in events if isinstance(event, TextDelta)] == [
        "He", "llo",
    ]
