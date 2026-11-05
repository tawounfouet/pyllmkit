"""Bounded sync and async stream consumers, without transport or I/O (ADR-035)."""

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from itertools import islice

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRunId

from .events import StreamEvent
from .protocols import AsyncInferenceStream, InferenceStream
from .reconstruction import MAX_EVENTS, StreamState, observe_eof, reduce_event, reduce_stream


def _validate_max_events(max_events: int | None) -> None:
    if max_events is not None and (
        type(max_events) is not int or not 0 <= max_events <= MAX_EVENTS
    ):
        raise DomainValidationError("max_events must be an integer from 0 to 100000 or None")


def consume_stream(
    stream: InferenceStream, *, max_events: int | None = None
) -> StreamState:
    """Reduce a synchronous pull stream; early stop retains INCOMPLETE evidence.

    Resource-owning iterators must be closed by their caller if interrupted.
    """
    _validate_max_events(max_events)
    events = iter(stream)
    bounded = events if max_events is None else islice(events, max_events)
    return reduce_stream(bounded, stream.run_id)


async def consume_async_stream(
    stream: AsyncInferenceStream, *, max_events: int | None = None
) -> StreamState:
    """Equivalent async reduction; no asyncio dependency inside the domain."""
    _validate_max_events(max_events)
    state = StreamState(stream.run_id)
    iterator = aiter(stream)
    count = 0
    while max_events is None or count < max_events:
        try:
            event = await anext(iterator)
        except StopAsyncIteration:
            break
        state = reduce_event(state, event)
        count += 1
    return observe_eof(state)


@dataclass(frozen=True, slots=True)
class MemoryInferenceStream:
    """Restartable, offline sync fixture; not an actual model invocation."""

    run_id: InferenceRunId
    events: tuple[StreamEvent, ...]

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId or type(self.events) is not tuple:
            raise DomainValidationError("MemoryInferenceStream expects run_id and events tuple")
        if any(not isinstance(event, StreamEvent) for event in self.events):
            raise DomainValidationError("MemoryInferenceStream contains non-stream events")

    def __iter__(self) -> Iterator[StreamEvent]:
        return iter(self.events)


@dataclass(frozen=True, slots=True)
class MemoryAsyncInferenceStream:
    """Restartable offline async fixture, implemented without a provider SDK."""

    run_id: InferenceRunId
    events: tuple[StreamEvent, ...]

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId or type(self.events) is not tuple:
            raise DomainValidationError("MemoryAsyncInferenceStream expects run_id and events tuple")
        if any(not isinstance(event, StreamEvent) for event in self.events):
            raise DomainValidationError("MemoryAsyncInferenceStream contains non-stream events")

    async def __aiter__(self) -> AsyncIterator[StreamEvent]:
        for event in self.events:
            yield event
