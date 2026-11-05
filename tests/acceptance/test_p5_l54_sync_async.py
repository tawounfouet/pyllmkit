"""P5-AC-025..032: sync/async delivery, cancellation and partial usage."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    AsyncInferenceStream,
    AsyncStreamingPort,
    InferenceStream,
    MemoryAsyncInferenceStream,
    MemoryInferenceStream,
    ResponseCancelled,
    ResponseCompleted,
    ResponseStarted,
    StreamEvent,
    StreamingPort,
    StreamSequenceGap,
    StreamStatus,
    TextDelta,
    UsageUpdated,
    consume_async_stream,
    consume_stream,
)


def fixtures() -> tuple[InferenceRunId, tuple[StreamEvent, ...]]:
    rid = InferenceRunId("p5-sync-async")
    return rid, (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="Bonjour "),
        TextDelta(run_id=rid, sequence=2, delta="Python"),
        UsageUpdated(run_id=rid, sequence=3, usage=Usage(output_tokens=2)),
        ResponseCompleted(run_id=rid, sequence=4),
    )


def test_p5_ac025_sync_iterator_and_protocol() -> None:
    rid, events = fixtures()
    stream: InferenceStream = MemoryInferenceStream(rid, events)
    assert tuple(iter(stream)) == events
    result = consume_stream(stream)
    assert result.status is StreamStatus.COMPLETED
    assert result.text == "Bonjour Python"


def test_p5_ac026_async_iterator_parity() -> None:
    async def run() -> None:
        rid, events = fixtures()
        stream: AsyncInferenceStream = MemoryAsyncInferenceStream(rid, events)
        collected = tuple([event async for event in stream])
        assert collected == events
        sync = consume_stream(MemoryInferenceStream(rid, events))
        async_result = await consume_async_stream(stream)
        assert async_result == sync
    asyncio.run(run())


def test_p5_ac027_explicit_cancellation_preserves_partial() -> None:
    rid = InferenceRunId("cancel")
    stream = MemoryInferenceStream(rid, (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="partial"),
        UsageUpdated(run_id=rid, sequence=2, usage=Usage(output_tokens=4)),
        ResponseCancelled(run_id=rid, sequence=3),
    ))
    observed = consume_stream(stream)
    assert observed.status is StreamStatus.CANCELLED and not observed.is_complete
    assert observed.text == "partial"
    assert observed.usage is not None and observed.usage.output_tokens == 4
    assert observed.usage.input_tokens is None
    assert not observed.usage_final


def test_p5_ac028_partial_stop_never_fakes_success() -> None:
    rid, events = fixtures()
    result = consume_stream(MemoryInferenceStream(rid, events), max_events=3)
    assert result.status is StreamStatus.INCOMPLETE
    assert result.text == "Bonjour Python"
    assert result.usage is None
    result_0 = consume_stream(MemoryInferenceStream(rid, events), max_events=0)
    assert result_0.status is StreamStatus.INCOMPLETE and result_0.text == ""


def test_p5_ac029_async_partial_usage_snapshot() -> None:
    async def run() -> None:
        rid = InferenceRunId("partial-usage")
        stream = MemoryAsyncInferenceStream(rid, (
            ResponseStarted(run_id=rid, sequence=0),
            UsageUpdated(run_id=rid, sequence=1, usage=Usage(input_tokens=7)),
            TextDelta(run_id=rid, sequence=2, delta="part"),
        ))
        result = await consume_async_stream(stream)
        assert result.status is StreamStatus.INCOMPLETE
        assert result.usage is not None
        assert result.usage.input_tokens == 7
        assert result.usage.output_tokens is None and not result.usage_final
    asyncio.run(run())


def test_p5_ac030_sync_generator_early_close_is_explicit() -> None:
    rid = InferenceRunId("sync-close")
    released: list[str] = []

    def source() -> Iterator[StreamEvent]:
        try:
            yield ResponseStarted(run_id=rid, sequence=0)
            yield TextDelta(run_id=rid, sequence=1, delta="partial")
            yield ResponseCompleted(run_id=rid, sequence=2)
        finally:
            released.append("closed")

    class Stream:
        run_id = rid

        def __init__(self) -> None:
            self.generator = source()

        def __iter__(self) -> Iterator[StreamEvent]:
            return self.generator

    stream = Stream()
    state = consume_stream(stream, max_events=2)
    assert state.status is StreamStatus.INCOMPLETE
    assert released == []
    stream.generator.close()
    assert released == ["closed"]


def test_p5_ac031_async_generator_explicit_aclose() -> None:
    async def run() -> None:
        rid = InferenceRunId("async-close")
        released: list[str] = []

        async def source() -> AsyncIterator[StreamEvent]:
            try:
                yield ResponseStarted(run_id=rid, sequence=0)
                yield TextDelta(run_id=rid, sequence=1, delta="partial")
                yield ResponseCompleted(run_id=rid, sequence=2)
            finally:
                released.append("closed")

        class Stream:
            run_id = rid

            def __init__(self) -> None:
                self.generator = source()

            def __aiter__(self) -> AsyncIterator[StreamEvent]:
                return self.generator

        stream = Stream()
        state = await consume_async_stream(stream, max_events=2)
        assert state.status is StreamStatus.INCOMPLETE
        assert not released
        await stream.generator.aclose()
        assert released == ["closed"]
    asyncio.run(run())


def test_p5_ac032_ports_are_only_contracts() -> None:
    assert hasattr(StreamingPort, "stream")
    assert hasattr(AsyncStreamingPort, "astream")
    assert not hasattr(MemoryInferenceStream, "invoke")
    assert not hasattr(MemoryAsyncInferenceStream, "execute")


def test_invalid_limit_rejected_for_sync_and_async() -> None:
    rid, events = fixtures()
    for invalid in (True, -1, 100_001, "3"):
        with pytest.raises(DomainValidationError, match="max_events"):
            consume_stream(MemoryInferenceStream(rid, events), max_events=cast(int, invalid))

    async def run() -> None:
        with pytest.raises(DomainValidationError, match="max_events"):
            await consume_async_stream(
                MemoryAsyncInferenceStream(rid, events), max_events=cast(int, False)
            )
    asyncio.run(run())


def test_async_ordering_error_is_identical_to_sync() -> None:
    async def run() -> None:
        rid = InferenceRunId("broken")
        events: tuple[StreamEvent, ...] = (
            ResponseStarted(run_id=rid, sequence=0),
            TextDelta(run_id=rid, sequence=3, delta="gap"),
        )
        with pytest.raises(StreamSequenceGap):
            consume_stream(MemoryInferenceStream(rid, events))
        with pytest.raises(StreamSequenceGap):
            await consume_async_stream(MemoryAsyncInferenceStream(rid, events))
    asyncio.run(run())


def test_memory_fixtures_validate_inputs() -> None:
    rid, events = fixtures()
    with pytest.raises(DomainValidationError, match="events tuple"):
        MemoryInferenceStream(rid, cast(tuple[StreamEvent, ...], [events[0]]))
    with pytest.raises(DomainValidationError, match="non-stream"):
        MemoryAsyncInferenceStream(rid, cast(tuple[StreamEvent, ...], ("x",)))
