"""Strict, standalone Streaming JSON v1 mapping codec (ADR-036).

Neither this codec nor the event domain parses text JSON, performs I/O,
reads provider credentials, or changes existing M1-M4 serialization.
"""

from collections.abc import Mapping, Sequence
from typing import cast

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import (
    FinishReason,
    FinishReasonCode,
    InferenceRunId,
    Usage,
)
from pyllmkit.domain.tooling import ToolCallId

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
from .reconstruction import reduce_stream

STREAMING_SCHEMA_VERSION = 1

_EVENT_FIELDS = frozenset({
    "schema_version", "object_type", "kind", "run_id", "sequence", "payload",
})
_TRACE_FIELDS = frozenset({
    "schema_version", "object_type", "run_id", "events", "observed_status",
})
_USAGE_FIELDS = frozenset({
    "input_tokens", "output_tokens", "total_tokens",
    "reasoning_tokens", "cached_input_tokens",
})
_FINISH_FIELDS = frozenset({"code", "native_reason"})
_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
    "response_started": frozenset(),
    "text_delta": frozenset({"delta"}),
    "tool_call_started": frozenset({"call_id", "tool_name"}),
    "tool_call_delta": frozenset({"call_id", "delta"}),
    "tool_call_completed": frozenset({"call_id"}),
    "usage_updated": frozenset({"usage", "is_final"}),
    "response_completed": frozenset({"finish_reason"}),
    "response_failed": frozenset({"reason_code"}),
    "response_cancelled": frozenset({"reason_code"}),
}
_TYPES = (
    ResponseStarted, TextDelta, ToolCallStarted, ToolCallDelta, ToolCallCompleted,
    UsageUpdated, ResponseCompleted, ResponseFailed, ResponseCancelled,
)


def _exact_object(value: object, fields: frozenset[str], label: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise DomainValidationError(f"{label} must be an object with string keys")
    data = cast(dict[str, object], value)
    if set(data) != fields:
        raise DomainValidationError(f"{label} has missing or unknown fields")
    return data


def _string(value: object, label: str) -> str:
    if type(value) is not str:
        raise DomainValidationError(f"{label} must be string")
    return value


def _nullable_string(value: object, label: str) -> str | None:
    return None if value is None else _string(value, label)


def _exact_int(value: object, label: str) -> int:
    if type(value) is not int:
        raise DomainValidationError(f"{label} must be exact integer")
    return value


def _version(data: dict[str, object], object_type: str) -> None:
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise DomainValidationError("unsupported Streaming JSON schema_version")
    if type(data["object_type"]) is not str or data["object_type"] != object_type:
        raise DomainValidationError("unsupported Streaming JSON object_type")


def _usage_to_dict(usage: Usage) -> dict[str, object]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
    }


def _usage_from_dict(value: object) -> Usage:
    data = _exact_object(value, _USAGE_FIELDS, "usage")
    counts: dict[str, int | None] = {}
    for key in _USAGE_FIELDS:
        raw = data[key]
        if raw is not None and (type(raw) is not int or raw < 0):
            raise DomainValidationError(f"usage.{key} must be nonnegative int or null")
        counts[key] = raw
    return Usage(**counts)


def _finish_to_dict(value: FinishReason | None) -> object:
    if value is None:
        return None
    return {"code": value.code.value, "native_reason": value.native_reason}


def _finish_from_dict(value: object) -> FinishReason | None:
    if value is None:
        return None
    data = _exact_object(value, _FINISH_FIELDS, "finish_reason")
    code = _string(data["code"], "finish_reason.code")
    if code not in {item.value for item in FinishReasonCode}:
        raise DomainValidationError("unsupported Streaming finish_reason code")
    native = _nullable_string(data["native_reason"], "finish_reason.native_reason")
    return FinishReason(FinishReasonCode(code), native)


def event_to_dict(event: StreamEvent) -> dict[str, object]:
    """Serialize exactly one known, immutable event without mutating it."""
    if type(event) not in _TYPES:
        raise DomainValidationError("unsupported StreamEvent type")
    payload: dict[str, object] = {}
    if isinstance(event, TextDelta):
        payload = {"delta": event.delta}
    elif isinstance(event, ToolCallStarted):
        payload = {"call_id": event.call_id.value, "tool_name": event.tool_name}
    elif isinstance(event, ToolCallDelta):
        payload = {"call_id": event.call_id.value, "delta": event.delta}
    elif isinstance(event, ToolCallCompleted):
        payload = {"call_id": event.call_id.value}
    elif isinstance(event, UsageUpdated):
        payload = {"usage": _usage_to_dict(event.usage), "is_final": event.is_final}
    elif isinstance(event, ResponseCompleted):
        payload = {"finish_reason": _finish_to_dict(event.finish_reason)}
    elif isinstance(event, (ResponseFailed, ResponseCancelled)):
        payload = {"reason_code": event.reason_code}
    return {
        "schema_version": STREAMING_SCHEMA_VERSION,
        "object_type": "stream_event",
        "kind": event.kind,
        "run_id": event.run_id.value,
        "sequence": event.sequence,
        "payload": payload,
    }


def event_from_dict(payload: Mapping[str, object]) -> StreamEvent:
    """Reject unknown fields, kinds, versions and wrongly typed values."""
    data = _exact_object(payload, _EVENT_FIELDS, "StreamEvent")
    _version(data, "stream_event")
    kind = _string(data["kind"], "kind")
    if kind not in _PAYLOAD_FIELDS:
        raise DomainValidationError("unsupported Streaming JSON kind")
    values = _exact_object(data["payload"], _PAYLOAD_FIELDS[kind], f"{kind} payload")
    run_id = InferenceRunId(_string(data["run_id"], "run_id"))
    sequence = _exact_int(data["sequence"], "sequence")
    if kind == "response_started":
        return ResponseStarted(run_id=run_id, sequence=sequence)
    if kind == "text_delta":
        return TextDelta(run_id=run_id, sequence=sequence, delta=_string(values["delta"], "delta"))
    if kind == "tool_call_started":
        return ToolCallStarted(
            run_id=run_id, sequence=sequence,
            call_id=ToolCallId(_string(values["call_id"], "call_id")),
            tool_name=_string(values["tool_name"], "tool_name"),
        )
    if kind == "tool_call_delta":
        return ToolCallDelta(
            run_id=run_id, sequence=sequence,
            call_id=ToolCallId(_string(values["call_id"], "call_id")),
            delta=_string(values["delta"], "delta"),
        )
    if kind == "tool_call_completed":
        return ToolCallCompleted(
            run_id=run_id, sequence=sequence,
            call_id=ToolCallId(_string(values["call_id"], "call_id")),
        )
    if kind == "usage_updated":
        is_final = values["is_final"]
        if type(is_final) is not bool:
            raise DomainValidationError("usage_updated.is_final must be exact boolean")
        return UsageUpdated(
            run_id=run_id, sequence=sequence,
            usage=_usage_from_dict(values["usage"]),
            is_final=is_final,
        )
    if kind == "response_completed":
        return ResponseCompleted(
            run_id=run_id, sequence=sequence,
            finish_reason=_finish_from_dict(values["finish_reason"]),
        )
    if kind == "response_failed":
        return ResponseFailed(
            run_id=run_id, sequence=sequence,
            reason_code=_string(values["reason_code"], "reason_code"),
        )
    if kind == "response_cancelled":
        return ResponseCancelled(
            run_id=run_id, sequence=sequence,
            reason_code=_string(values["reason_code"], "reason_code"),
        )
    raise DomainValidationError("unsupported Streaming JSON event")


def stream_to_dict(events: Sequence[StreamEvent], run_id: InferenceRunId) -> dict[str, object]:
    """Encode a validated stream trace with an explicit observed terminality."""
    if type(run_id) is not InferenceRunId:
        raise DomainValidationError("stream_to_dict requires an InferenceRunId")
    if any(type(event) not in _TYPES for event in events):
        raise DomainValidationError("stream_to_dict expects StreamEvent values")
    state = reduce_stream(events, run_id)
    return {
        "schema_version": STREAMING_SCHEMA_VERSION,
        "object_type": "stream_trace",
        "run_id": run_id.value,
        "events": [event_to_dict(event) for event in events],
        "observed_status": state.status.value,
    }


def stream_from_dict(payload: Mapping[str, object]) -> tuple[InferenceRunId, tuple[StreamEvent, ...]]:
    """Decode and replay; reject fabricated completion or changed correlation."""
    data = _exact_object(payload, _TRACE_FIELDS, "stream_trace")
    _version(data, "stream_trace")
    run_id = InferenceRunId(_string(data["run_id"], "run_id"))
    values = data["events"]
    if type(values) is not list:
        raise DomainValidationError("stream_trace.events must be an array")
    events = tuple(event_from_dict(cast(Mapping[str, object], item)) for item in values)
    state = reduce_stream(events, run_id)
    claimed = _string(data["observed_status"], "observed_status")
    if claimed != state.status.value:
        raise DomainValidationError("stream_trace observed_status mismatches replay")
    return run_id, events
