"""Lightweight stream protocol identity; consumers and adapters are L5.4."""

from collections.abc import AsyncIterator, Iterator
from typing import Protocol

from pyllmkit.domain.inference import InferenceRequest, InferenceRunId

from .events import StreamEvent


class InferenceStream(Protocol):
    """Behavioral typed stream abstraction, not an InferenceRun aggregate."""

    @property
    def run_id(self) -> InferenceRunId:
        ...

    def __iter__(self) -> Iterator[StreamEvent]:
        ...


class AsyncInferenceStream(Protocol):
    """Asynchronous pull stream, independent from any transport implementation."""

    @property
    def run_id(self) -> InferenceRunId:
        ...

    def __aiter__(self) -> AsyncIterator[StreamEvent]:
        ...


class StreamingPort(Protocol):
    """Future sync provider adapter port; no provider is implemented here."""

    def stream(self, request: InferenceRequest) -> Iterator[StreamEvent]:
        ...


class AsyncStreamingPort(Protocol):
    """Return an AsyncIterator directly, without a preliminary await."""

    def astream(self, request: InferenceRequest) -> AsyncIterator[StreamEvent]:
        ...
