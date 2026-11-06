"""S5 native streaming session lifecycle conformance for six providers.

HTTPX MockTransport and tracked ByteStream objects only; no real sockets,
credentials or remote billing. Mid-stream cancellation is local and
cooperative, and cannot be represented as provider-side cancellation.
"""

import asyncio

import httpx
import pytest

from pyllmkit.application.inference import (
    AsyncStreamingSession,
    InvocationPreconditionError,
    StreamingSession,
)
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseStarted,
    TextDelta,
)
from tests.conformance.providers import PROVIDERS, prepared
from tests.conformance.stream_fixtures import stream_mime, stream_wire
from tests.conformance.test_v030_s2_native_streaming import _stream_adapter


class TrackedSync(httpx.SyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.closed = False

    def __iter__(self):
        yield self.data

    def close(self) -> None:
        self.closed = True


class TrackedAsync(httpx.AsyncByteStream):
    def __init__(self, data: bytes, *, block_after_first_chunk: bool = False) -> None:
        self.data = data
        self.block_after_first_chunk = block_after_first_chunk
        self.closed = False
        self.waiting = asyncio.Event()

    async def __aiter__(self):
        yield self.data
        if self.block_after_first_chunk:
            self.waiting.set()
            await asyncio.Event().wait()

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_cancel_after_first_delta_closes_native_mock_transport(
    provider: str, async_mode: bool,
) -> None:
    content = stream_wire(provider)
    tracked = TrackedAsync(content) if async_mode else TrackedSync(content)
    calls: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, headers={"content-type": stream_mime(provider)}, stream=tracked,
        )

    port = _stream_adapter(provider, handler=responder)
    case = prepared(provider)
    if async_mode:
        session = AsyncStreamingSession(case, port)

        async def collect() -> tuple[object, object, list[object]]:
            iterator = aiter(session)
            first, second = await anext(iterator), await anext(iterator)
            session.cancel()
            tail = [event async for event in iterator]
            return first, second, tail

        first, second, tail = asyncio.run(collect())
    else:
        session = StreamingSession(case, port)
        iterator = iter(session)
        first, second = next(iterator), next(iterator)
        session.cancel()
        tail = list(iterator)

    assert isinstance(first, ResponseStarted)
    assert isinstance(second, TextDelta)
    assert len(tail) == 1
    assert isinstance(tail[0], ResponseCancelled)
    assert tail[0].reason_code == "user_cancelled"
    assert [first.sequence, second.sequence, tail[0].sequence] == [0, 1, 2]
    assert all(event.run_id == session.run_id for event in (first, second, *tail))
    assert tracked.closed is True
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_single_use_stream_session_rejects_replay_without_second_call(
    provider: str, async_mode: bool,
) -> None:
    calls: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("unconsumed iterator must not contact transport")

    port = _stream_adapter(provider, handler=responder)
    case = prepared(provider)
    if async_mode:
        session = AsyncStreamingSession(case, port)

        async def run() -> None:
            source = aiter(session)
            with pytest.raises(
                InvocationPreconditionError, match="stream_session_already_consumed",
            ):
                aiter(session)
            await source.aclose()

        asyncio.run(run())
    else:
        session = StreamingSession(case, port)
        source = iter(session)
        with pytest.raises(
            InvocationPreconditionError, match="stream_session_already_consumed",
        ):
            iter(session)
        source.close()
    assert calls == []


@pytest.mark.parametrize("provider", PROVIDERS)
def test_external_async_task_cancel_propagates_and_closes_native_mock_socket(
    provider: str,
) -> None:
    tracked = TrackedAsync(stream_wire(provider, truncate=True), block_after_first_chunk=True)
    calls: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, headers={"content-type": stream_mime(provider)}, stream=tracked,
        )

    session = AsyncStreamingSession(
        prepared(provider), _stream_adapter(provider, handler=responder),
    )

    async def run() -> None:
        iterator = aiter(session)
        emitted = [await anext(iterator) for _ in range(3)]
        assert isinstance(emitted[0], ResponseStarted)
        assert all(isinstance(event, TextDelta) for event in emitted[1:])
        waiter = asyncio.create_task(anext(iterator))
        await asyncio.wait_for(tracked.waiting.wait(), timeout=1)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        await iterator.aclose()

    asyncio.run(run())
    assert tracked.closed is True
    assert len(calls) == 1


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("async_mode", (False, True), ids=("sync", "async"))
def test_cancel_after_completed_stream_has_no_second_terminal(
    provider: str, async_mode: bool,
) -> None:
    content = stream_wire(provider)
    calls: list[httpx.Request] = []

    def responder(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, headers={"content-type": stream_mime(provider)}, content=content,
        )

    port = _stream_adapter(provider, handler=responder)
    case = prepared(provider)
    if async_mode:
        session = AsyncStreamingSession(case, port)

        async def run() -> tuple[list[object], list[object]]:
            iterator = aiter(session)
            events = [event async for event in iterator]
            session.cancel()
            return events, [event async for event in iterator]

        events, extra = asyncio.run(run())
    else:
        session = StreamingSession(case, port)
        iterator = iter(session)
        events = list(iterator)
        session.cancel()
        extra = list(iterator)

    assert isinstance(events[-1], ResponseCompleted)
    assert not any(isinstance(event, ResponseCancelled) for event in events)
    assert sum(isinstance(event, ResponseCompleted) for event in events) == 1
    assert extra == []
    assert len(calls) == 1
