"""P7 L7.7 provider-independent, cooperative stream cancellation.

The cancellation signal is scoped to one streaming session. It cancels local
consumption only, never claims cancellation of a remote inference request.
The sync wrapper cannot interrupt an already-blocking native read. Async task
cancellation still propagates so that the transport's finally closes sockets.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from threading import Event
from typing import TypeVar

from pyllmkit.domain.inference import InferenceRunId
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamEvent,
)

_Terminal = (ResponseCompleted, ResponseFailed, ResponseCancelled)
_TStream = TypeVar("_TStream")


class StreamCancellationSignal:
    """Thread-safe one-way cancellation flag, scoped to one logical run."""

    __slots__ = ("_flag",)

    def __init__(self) -> None:
        self._flag = Event()

    def cancel(self) -> None:
        self._flag.set()

    @property
    def cancelled(self) -> bool:
        return self._flag.is_set()


def _cancel_events(run_id: InferenceRunId, sequence: int) -> Iterator[StreamEvent]:
    if sequence == 0:
        yield ResponseStarted(run_id=run_id, sequence=0)
        sequence += 1
    yield ResponseCancelled(run_id=run_id, sequence=sequence, reason_code="user_cancelled")


def iter_resilient(
    source_factory: Callable[[], Iterator[StreamEvent]],
    run_id: InferenceRunId,
    signal: StreamCancellationSignal,
) -> Iterator[StreamEvent]:
    """Yield a single terminal event; eagerly close the source on cancellation."""
    source: Iterator[StreamEvent] | None = None
    sequence = 0
    try:
        while True:
            if signal.cancelled:
                yield from _cancel_events(run_id, sequence)
                return
            if source is None:
                source = source_factory()
            try:
                event = next(source)
            except StopIteration:
                yield ResponseFailed(
                    run_id=run_id, sequence=sequence, reason_code="provider_not_completed",
                )
                return
            if signal.cancelled:
                yield from _cancel_events(run_id, sequence)
                return
            yield event
            sequence = event.sequence + 1
            if isinstance(event, _Terminal):
                return
    finally:
        if source is not None:
            close = getattr(source, "close", None)
            if callable(close):
                close()


async def aiter_resilient(
    source_factory: Callable[[], AsyncIterator[StreamEvent]],
    run_id: InferenceRunId,
    signal: StreamCancellationSignal,
) -> AsyncIterator[StreamEvent]:
    """Async session wrapper; caller task cancellation remains externally visible."""
    source: AsyncIterator[StreamEvent] | None = None
    sequence = 0
    try:
        while True:
            if signal.cancelled:
                for item in _cancel_events(run_id, sequence):
                    yield item
                return
            if source is None:
                source = source_factory()
            try:
                event = await anext(source)
            except StopAsyncIteration:
                yield ResponseFailed(
                    run_id=run_id, sequence=sequence, reason_code="provider_not_completed",
                )
                return
            if signal.cancelled:
                for item in _cancel_events(run_id, sequence):
                    yield item
                return
            yield event
            sequence = event.sequence + 1
            if isinstance(event, _Terminal):
                return
    finally:
        if source is not None:
            close = getattr(source, "aclose", None)
            if callable(close):
                await close()
