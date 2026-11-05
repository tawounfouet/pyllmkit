"""Pure event reducer and deterministic text reconstruction (ADR-031/032/034)."""

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import StrEnum

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.tooling.identifiers import ToolCallId

from .errors import (
    StreamDuplicateSequence,
    StreamLifecycleError,
    StreamLimitError,
    StreamOutOfOrder,
    StreamRunMismatch,
    StreamSequenceGap,
    StreamToolCallError,
)
from .events import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamEvent,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    UsageUpdated,
)

MAX_EVENTS = 100_000
MAX_TEXT_BYTES = 8 * 1024 * 1024
MAX_TOOL_CALLS = 128


class StreamStatus(StrEnum):
    CREATED = "created"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class _TextPart:
    value: str = field(repr=False)
    previous: "_TextPart | None" = field(repr=False)


@dataclass(frozen=True, slots=True)
class StreamState:
    """Immutable reduction snapshot, not an InferenceRun or final InferenceResponse."""

    run_id: InferenceRunId
    status: StreamStatus = StreamStatus.CREATED
    next_sequence: int = 0
    _text_tail: _TextPart | None = field(default=None, repr=False)
    text_size_bytes: int = 0
    usage: Usage | None = None
    usage_final: bool = False
    error_code: str | None = field(default=None, repr=False)
    _opened: tuple[ToolCallId, ...] = field(default=(), repr=False)
    _seen: tuple[ToolCallId, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("StreamState.run_id must be InferenceRunId")

    @property
    def last_sequence(self) -> int:
        return self.next_sequence - 1

    @property
    def is_complete(self) -> bool:
        return self.status is StreamStatus.COMPLETED

    @property
    def text(self) -> str:
        """Join an immutable linked list once, not at every incoming delta."""
        parts: list[str] = []
        node = self._text_tail
        while node is not None:
            parts.append(node.value)
            node = node.previous
        return "".join(reversed(parts))


def reduce_event(state: StreamState, event: StreamEvent) -> StreamState:
    """Return a new state for one ordered event, or raise a payload-free error."""
    if type(event) not in (
        ResponseStarted, TextDelta, ToolCallStarted, ToolCallDelta,
        ToolCallCompleted, UsageUpdated, ResponseCompleted, ResponseFailed,
        ResponseCancelled,
    ):
        raise StreamLifecycleError("unsupported streaming event kind")
    if state.run_id != event.run_id:
        raise StreamRunMismatch("stream run mismatch")
    if event.sequence < state.next_sequence:
        if event.sequence == state.next_sequence - 1:
            raise StreamDuplicateSequence("duplicate stream sequence")
        raise StreamOutOfOrder("out of order stream sequence")
    if event.sequence > state.next_sequence:
        raise StreamSequenceGap("stream sequence gap")
    if state.next_sequence >= MAX_EVENTS:
        raise StreamLimitError("stream event count exceeded")
    if state.status not in (StreamStatus.CREATED, StreamStatus.STARTED):
        raise StreamLifecycleError("stream is already terminal or observed incomplete")
    if state.status is StreamStatus.CREATED:
        if type(event) is not ResponseStarted:
            raise StreamLifecycleError("stream must begin with ResponseStarted")
        return replace(state, status=StreamStatus.STARTED, next_sequence=1)
    if type(event) is ResponseStarted:
        raise StreamLifecycleError("duplicate ResponseStarted")

    next_state = replace(state, next_sequence=state.next_sequence + 1)
    if isinstance(event, TextDelta):
        size = len(event.delta.encode("utf-8"))
        if state.text_size_bytes + size > MAX_TEXT_BYTES:
            raise StreamLimitError("stream text byte budget exceeded")
        return replace(
            next_state,
            _text_tail=_TextPart(event.delta, state._text_tail),
            text_size_bytes=state.text_size_bytes + size,
        )
    if isinstance(event, ToolCallStarted):
        if event.call_id in state._seen:
            raise StreamToolCallError("tool call ID already used")
        if len(state._seen) >= MAX_TOOL_CALLS:
            raise StreamLimitError("tool call count budget exceeded")
        return replace(
            next_state,
            _opened=state._opened + (event.call_id,),
            _seen=state._seen + (event.call_id,),
        )
    if isinstance(event, (ToolCallDelta, ToolCallCompleted)):
        if event.call_id not in state._opened:
            raise StreamToolCallError("tool call not open")
        if isinstance(event, ToolCallCompleted):
            return replace(
                next_state,
                _opened=tuple(x for x in state._opened if x != event.call_id),
            )
        return next_state  # L5.3 introduces raw argument reassembly per ID.
    if isinstance(event, UsageUpdated):
        if state.usage_final:
            raise StreamLifecycleError("usage already marked final")
        return replace(next_state, usage=event.usage, usage_final=event.is_final)
    if isinstance(event, ResponseCompleted):
        if state._opened:
            raise StreamLifecycleError("cannot complete stream with open tool calls")
        return replace(next_state, status=StreamStatus.COMPLETED)
    if isinstance(event, ResponseFailed):
        return replace(next_state, status=StreamStatus.FAILED, error_code=event.reason_code)
    if isinstance(event, ResponseCancelled):
        return replace(next_state, status=StreamStatus.CANCELLED, error_code=event.reason_code)
    raise StreamLifecycleError("unhandled streaming event kind")


def observe_eof(state: StreamState) -> StreamState:
    """An EOF without terminal means incomplete evidence, never a success."""
    if state.status in (StreamStatus.CREATED, StreamStatus.STARTED):
        return replace(state, status=StreamStatus.INCOMPLETE)
    return state


def reduce_stream(events: Iterable[StreamEvent], run_id: InferenceRunId) -> StreamState:
    """Replay an offline stream and classify any unproven EOF as incomplete."""
    state = StreamState(run_id)
    for event in events:
        state = reduce_event(state, event)
    return observe_eof(state)
