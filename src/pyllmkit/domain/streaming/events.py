"""P5 stream events: immutable, provider-free observations (ADR-030..033, 037)."""

from dataclasses import dataclass, field
from typing import ClassVar

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import FinishReason, InferenceRunId, Usage
from pyllmkit.domain.tooling.definitions import validate_tool_name
from pyllmkit.domain.tooling.identifiers import ToolCallId

MAX_SEQUENCE = 2**63 - 1
MAX_DELTA_BYTES = 1_048_576


def _check_reason(code: str) -> None:
    if type(code) is not str or not (1 <= len(code) <= 64):
        raise DomainValidationError("stream reason_code must be a nonblank code of at most 64 chars")
    if not code.replace("_", "").replace("-", "").isalnum() or not code.isascii():
        raise DomainValidationError("stream reason_code must contain only ASCII letters, digits, _ or -")


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamEvent:
    """Base value object: an exact position in one run, not a durable DomainEvent."""

    run_id: InferenceRunId
    sequence: int
    kind: ClassVar[str] = "stream_event"

    def __post_init__(self) -> None:
        if type(self) is StreamEvent:
            raise DomainValidationError("StreamEvent is an abstract event family")
        if type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("StreamEvent.run_id must be InferenceRunId")
        if type(self.sequence) is not int or not (0 <= self.sequence <= MAX_SEQUENCE):
            raise DomainValidationError("StreamEvent.sequence must be a bounded nonnegative int")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseStarted(StreamEvent):
    kind: ClassVar[str] = "response_started"


@dataclass(frozen=True, slots=True, kw_only=True)
class TextDelta(StreamEvent):
    delta: str = field(repr=False)
    kind: ClassVar[str] = "text_delta"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if type(self.delta) is not str:
            raise DomainValidationError("TextDelta.delta must be a string")
        if len(self.delta.encode("utf-8")) > MAX_DELTA_BYTES:
            raise DomainValidationError("TextDelta.delta size limit exceeded")


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolCallStarted(StreamEvent):
    call_id: ToolCallId
    tool_name: str
    kind: ClassVar[str] = "tool_call_started"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if type(self.call_id) is not ToolCallId:
            raise DomainValidationError("ToolCallStarted.call_id must be ToolCallId")
        validate_tool_name(self.tool_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolCallDelta(StreamEvent):
    call_id: ToolCallId
    delta: str = field(repr=False)
    kind: ClassVar[str] = "tool_call_delta"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if type(self.call_id) is not ToolCallId:
            raise DomainValidationError("ToolCallDelta.call_id must be ToolCallId")
        if type(self.delta) is not str:
            raise DomainValidationError("ToolCallDelta.delta must be a string")
        if len(self.delta.encode("utf-8")) > MAX_DELTA_BYTES:
            raise DomainValidationError("ToolCallDelta.delta size limit exceeded")


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolCallCompleted(StreamEvent):
    call_id: ToolCallId
    kind: ClassVar[str] = "tool_call_completed"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if type(self.call_id) is not ToolCallId:
            raise DomainValidationError("ToolCallCompleted.call_id must be ToolCallId")


@dataclass(frozen=True, slots=True, kw_only=True)
class UsageUpdated(StreamEvent):
    usage: Usage
    is_final: bool = False
    kind: ClassVar[str] = "usage_updated"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if type(self.usage) is not Usage:
            raise DomainValidationError("UsageUpdated.usage must be Usage")
        if type(self.is_final) is not bool:
            raise DomainValidationError("UsageUpdated.is_final must be an exact boolean")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseCompleted(StreamEvent):
    finish_reason: FinishReason | None = field(default=None, repr=False)
    kind: ClassVar[str] = "response_completed"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        if self.finish_reason is not None and type(self.finish_reason) is not FinishReason:
            raise DomainValidationError("ResponseCompleted.finish_reason must be FinishReason or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseFailed(StreamEvent):
    reason_code: str
    kind: ClassVar[str] = "response_failed"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        _check_reason(self.reason_code)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseCancelled(StreamEvent):
    reason_code: str = "cancelled"
    kind: ClassVar[str] = "response_cancelled"

    def __post_init__(self) -> None:
        StreamEvent.__post_init__(self)
        _check_reason(self.reason_code)
