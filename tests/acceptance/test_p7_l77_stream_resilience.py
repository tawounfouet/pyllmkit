"""P7-G7: cancellation, deadlines and fail-closed streaming (offline only)."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from test_p7_l76_native_streaming import PROVIDERS, service

from pyllmkit.adapters.inference import NativeProviderStreamingAdapter
from pyllmkit.adapters.inference import native_stream_transport as transport_module
from pyllmkit.application.inference.streaming_resilience import (
    StreamCancellationSignal,
    aiter_resilient,
    iter_resilient,
)
from pyllmkit.domain.inference import InferenceRunId
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    TextDelta,
)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_sync_cancel_before_first_pull_does_not_enter_adapter(provider: str) -> None:
    sync, _, request, snapshot = service(provider)
    session = sync.open_stream(request, snapshot)
    session.cancel()
    assert session.cancelled
    events = list(session)
    assert [type(e) for e in events] == [ResponseStarted, ResponseCancelled]
    assert [e.sequence for e in events] == [0, 1]
    assert all(e.run_id == session.run_id for e in events)
    assert events[-1].reason_code == "user_cancelled"
    assert not any(isinstance(e, ResponseCompleted) for e in events)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_sync_cancel_after_delta_prevents_completion(provider: str) -> None:
    sync, _, request, snapshot = service(provider)
    session = sync.open_stream(request, snapshot)
    stream = iter(session)
    assert isinstance(next(stream), ResponseStarted)
    assert isinstance(next(stream), TextDelta)
    session.cancel()
    remaining = list(stream)
    assert len(remaining) == 1
    assert isinstance(remaining[0], ResponseCancelled)
    assert remaining[0].sequence == 2
    assert remaining[0].run_id == session.run_id


@pytest.mark.parametrize("provider", PROVIDERS)
def test_async_cancel_before_start_emits_local_terminal(provider: str) -> None:
    _, async_service, request, snapshot = service(provider)
    session = async_service.open_astream(request, snapshot)
    session.cancel()

    async def run() -> list[object]:
        return [event async for event in session]

    events = asyncio.run(run())
    assert [type(e) for e in events] == [ResponseStarted, ResponseCancelled]
    assert [e.sequence for e in events] == [0, 1]
    assert events[-1].reason_code == "user_cancelled"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_async_cancel_after_delta_prevents_completion(provider: str) -> None:
    _, async_service, request, snapshot = service(provider)
    session = async_service.open_astream(request, snapshot)

    async def run() -> list[object]:
        stream = aiter(session)
        first = await anext(stream)
        second = await anext(stream)
        assert isinstance(first, ResponseStarted)
        assert isinstance(second, TextDelta)
        session.cancel()
        return [item async for item in stream]

    remaining = asyncio.run(run())
    assert len(remaining) == 1
    assert isinstance(remaining[0], ResponseCancelled)
    assert remaining[0].sequence == 2
    assert remaining[0].run_id == session.run_id


def test_cancel_signal_is_scoped_to_one_stream_session() -> None:
    sync, _, request, snapshot = service("ollama")
    first = sync.open_stream(request, snapshot)
    second = sync.open_stream(request, snapshot)
    assert first.run_id != second.run_id
    first.cancel()
    assert isinstance(list(first)[-1], ResponseCancelled)
    assert isinstance(list(second)[-1], ResponseCompleted)


def test_cancel_after_terminal_does_not_emit_second_terminal() -> None:
    sync, _, request, snapshot = service("openai")
    session = sync.open_stream(request, snapshot)
    stream = iter(session)
    events = list(stream)
    assert isinstance(events[-1], ResponseCompleted)
    session.cancel()
    assert list(stream) == []


def test_cancel_signal_is_idempotent_and_one_way() -> None:
    flag = StreamCancellationSignal()
    assert not flag.cancelled
    flag.cancel()
    flag.cancel()
    assert flag.cancelled


def test_generic_sync_port_early_eof_cannot_be_success() -> None:
    run = InferenceRunId("test-run")
    events = list(iter_resilient(
        lambda: iter((ResponseStarted(run_id=run, sequence=0),)),
        run, StreamCancellationSignal(),
    ))
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_not_completed"
    assert events[-1].sequence == 1


def test_generic_async_port_early_eof_cannot_be_success() -> None:
    run = InferenceRunId("test-run")

    async def source():
        yield ResponseStarted(run_id=run, sequence=0)

    async def collect() -> list[object]:
        return [event async for event in aiter_resilient(
            source, run, StreamCancellationSignal(),
        )]

    events = asyncio.run(collect())
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].sequence == 1


@pytest.mark.parametrize("provider", PROVIDERS)
def test_real_sync_socket_is_rejected_before_credential_resolution(provider: str) -> None:
    sync, _, request, snapshot = service(provider)
    existing = sync.open_stream(request, snapshot)
    guarded = NativeProviderStreamingAdapter(
        existing.adapter.config,
        existing.adapter.credentials,
        allow_live=True,
    )
    events = list(guarded.stream_prepared(existing.prepared))
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "sync_stream_deadline_not_enforceable"
    assert not any(isinstance(event, ResponseCompleted) for event in events)


def test_sync_monotonic_budget_stops_trickle_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    sync, _, request, snapshot = service("ollama")
    prepared = sync.open_stream(request, snapshot).prepared
    monkeypatch.setattr(transport_module, "monotonic", lambda: 101.0)
    with pytest.raises(Exception, match="provider_timeout"):
        list(transport_module._sync_budget_lines(
            iter(("safe",)), started_at=100.0, budget_seconds=1.0,
            prepared=prepared,
        ))


def test_sync_budget_accepts_early_valid_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    sync, _, request, snapshot = service("ollama")
    prepared = sync.open_stream(request, snapshot).prepared
    monkeypatch.setattr(transport_module, "monotonic", lambda: 100.5)
    assert list(transport_module._sync_budget_lines(
        iter(("first", "second")), started_at=100.0, budget_seconds=1.0,
        prepared=prepared,
    )) == ["first", "second"]


def test_async_external_task_cancel_propagates_and_closes_socket() -> None:
    class Stream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            yield (
                b'{"model":"llama-synthetic","message":'
                b'{"role":"assistant","content":"He"},"done":false}\n'
            )
            await asyncio.Event().wait()

        async def aclose(self) -> None:
            self.closed = True

    raw_stream = Stream()
    _, async_service, request, snapshot = service("ollama")
    session = async_service.open_astream(request, snapshot)
    adapter = NativeProviderStreamingAdapter(
        session.adapter.config, session.adapter.credentials, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            200, stream=raw_stream, headers={"content-type": "application/x-ndjson"},
        )),
    )

    async def run() -> None:
        source = adapter.astream_prepared(session.prepared)
        assert isinstance(await anext(source), ResponseStarted)
        assert isinstance(await anext(source), TextDelta)
        waiter = asyncio.create_task(anext(source))
        await asyncio.sleep(0.01)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        await source.aclose()

    asyncio.run(run())
    assert raw_stream.closed is True


def test_async_total_deadline_closes_trickling_stream() -> None:
    class Trickle(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            while True:
                await asyncio.sleep(0.01)
                yield b": heartbeat\n\n"

        async def aclose(self) -> None:
            self.closed = True

    stream = Trickle()
    _, async_service, request, snapshot = service("anthropic")
    session = async_service.open_astream(request, snapshot)
    short = replace(session.prepared, context=replace(
        session.prepared.context, deadline=datetime.now(UTC) + timedelta(seconds=0.06),
    ))
    adapter = NativeProviderStreamingAdapter(
        session.adapter.config, session.adapter.credentials, allow_live=True,
        _test_transport=httpx.MockTransport(lambda _: httpx.Response(
            200, stream=stream, headers={"content-type": "text/event-stream"},
        )),
    )

    async def run() -> list[object]:
        return [item async for item in adapter.astream_prepared(short)]

    events = asyncio.run(run())
    assert isinstance(events[0], ResponseStarted)
    assert isinstance(events[-1], ResponseFailed)
    assert events[-1].reason_code == "provider_timeout"
    assert stream.closed is True
