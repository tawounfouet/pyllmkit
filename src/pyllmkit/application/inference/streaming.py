"""P7 L7.6 application streaming sessions, preserving unchanged M5 protocols.

The invocation pipeline prepares once with M6 resolution and a RunId.
Streaming observation is M5 StreamState, not an invented terminal InferenceRun.
No infrastructure imports in this module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from dataclasses import dataclass, field
from threading import Lock

from pyllmkit.application.inference.contracts import (
    InvocationOptions,
    InvocationPreconditionError,
    PreparedInvocation,
)
from pyllmkit.application.inference.service import _InvocationPipeline
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.inference import (
    DeploymentId,
    GenerationSupportSnapshot,
    InferenceRequest,
    InferenceRunId,
)
from pyllmkit.domain.streaming import StreamEvent
from pyllmkit.protocols.inference import (
    AsyncPreparedStreamingPort,
    PreparedStreamingPort,
)


class _OneShot:
    """Prevent replaying a paid network invocation with one logical RunId."""

    __slots__ = ("_lock", "_claimed")

    def __init__(self) -> None:
        self._lock = Lock()
        self._claimed = False

    def claim(self) -> None:
        with self._lock:
            if self._claimed:
                raise InvocationPreconditionError("stream_session_already_consumed")
            self._claimed = True


@dataclass(frozen=True, slots=True)
class StreamingSession:
    """Single-use lazily consumed live stream, exposing the allocated RunId."""

    prepared: PreparedInvocation = field(repr=False)
    adapter: PreparedStreamingPort = field(repr=False)
    _one_shot: _OneShot = field(default_factory=_OneShot, repr=False, compare=False)

    @property
    def run_id(self) -> InferenceRunId:
        return self.prepared.context.run_id

    def __iter__(self) -> Iterator[StreamEvent]:
        self._one_shot.claim()
        return self.adapter.stream_prepared(self.prepared)


@dataclass(frozen=True, slots=True)
class AsyncStreamingSession:
    """Native async iterator, no preliminary await and no blocking provider I/O."""

    prepared: PreparedInvocation = field(repr=False)
    adapter: AsyncPreparedStreamingPort = field(repr=False)
    _one_shot: _OneShot = field(default_factory=_OneShot, repr=False, compare=False)

    @property
    def run_id(self) -> InferenceRunId:
        return self.prepared.context.run_id

    def __aiter__(self) -> AsyncIterator[StreamEvent]:
        self._one_shot.claim()
        return self.adapter.astream_prepared(self.prepared)


class StreamingInferenceService:
    """Deployment-bound streaming adapters, no fallback or semantic role merging."""

    __slots__ = ("_pipeline", "_bindings")

    def __init__(
        self,
        resolver: DeploymentResolver,
        adapter_bindings: Mapping[DeploymentId, PreparedStreamingPort],
        model_alias_bindings: Mapping[DeploymentId, str],
        *,
        options: InvocationOptions | None = None,
    ) -> None:
        self._pipeline = _InvocationPipeline(resolver, model_alias_bindings, options=options)
        self._bindings = dict(adapter_bindings)
        if any(type(key) is not DeploymentId or not isinstance(value, PreparedStreamingPort)
               for key, value in self._bindings.items()):
            raise TypeError("invalid_streaming_adapter_binding")

    def open_stream(
        self, request: InferenceRequest,
        support_snapshot: GenerationSupportSnapshot | None = None,
    ) -> StreamingSession:
        prepared, _running = self._pipeline.prepare(request, support_snapshot)
        adapter = self._bindings.get(prepared.context.deployment_id)
        if adapter is None:
            raise InvocationPreconditionError("streaming_adapter_not_registered")
        return StreamingSession(prepared, adapter)

    def stream(self, request: InferenceRequest) -> Iterator[StreamEvent]:
        """M5-compatible port: no signature or return-type changes."""
        return iter(self.open_stream(request))


class AsyncStreamingInferenceService:
    """Async counterpart: .astream returns AsyncIterator directly."""

    __slots__ = ("_pipeline", "_bindings")

    def __init__(
        self,
        resolver: DeploymentResolver,
        adapter_bindings: Mapping[DeploymentId, AsyncPreparedStreamingPort],
        model_alias_bindings: Mapping[DeploymentId, str],
        *,
        options: InvocationOptions | None = None,
    ) -> None:
        self._pipeline = _InvocationPipeline(resolver, model_alias_bindings, options=options)
        self._bindings = dict(adapter_bindings)
        if any(type(key) is not DeploymentId or not isinstance(value, AsyncPreparedStreamingPort)
               for key, value in self._bindings.items()):
            raise TypeError("invalid_async_streaming_adapter_binding")

    def open_astream(
        self, request: InferenceRequest,
        support_snapshot: GenerationSupportSnapshot | None = None,
    ) -> AsyncStreamingSession:
        prepared, _running = self._pipeline.prepare(request, support_snapshot)
        adapter = self._bindings.get(prepared.context.deployment_id)
        if adapter is None:
            raise InvocationPreconditionError("streaming_adapter_not_registered")
        return AsyncStreamingSession(prepared, adapter)

    def astream(self, request: InferenceRequest) -> AsyncIterator[StreamEvent]:
        """M5-compatible async API, with no initial await."""
        return self.open_astream(request).__aiter__()
