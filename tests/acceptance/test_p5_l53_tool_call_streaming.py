"""P5-AC-017..024: streamed tool calls remain descriptive and raw-only."""

from dataclasses import FrozenInstanceError
from typing import TypeVar

import pytest

from pyllmkit.domain.inference import InferenceRunId
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamLimitError,
    StreamState,
    StreamStatus,
    StreamToolCallError,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    reduce_event,
    reduce_stream,
)
from pyllmkit.domain.tooling import ToolCall, ToolCallId

T = TypeVar("T")


def event(kind: type[T], seq: int, **kwargs: object) -> T:
    return kind(run_id=InferenceRunId("r"), sequence=seq, **kwargs)


def test_p5_ac017_unknown_call_delta_rejected() -> None:
    with pytest.raises(StreamToolCallError):
        reduce_stream(
            [
                event(ResponseStarted, 0),
                event(ToolCallDelta, 1, call_id=ToolCallId("unknown"), delta="x"),
            ],
            InferenceRunId("r"),
        )


def test_p5_ac018_interleaved_calls_have_exact_independent_buffers() -> None:
    a, b = ToolCallId("A"), ToolCallId("B")
    events = [
        event(ResponseStarted, 0),
        event(ToolCallStarted, 1, call_id=a, tool_name="weather"),
        event(ToolCallStarted, 2, call_id=b, tool_name="calendar"),
        event(ToolCallDelta, 3, call_id=a, delta='{"city":'),
        event(ToolCallDelta, 4, call_id=b, delta='{"day":'),
        event(ToolCallDelta, 5, call_id=a, delta='"Paris"}'),
        event(ToolCallCompleted, 6, call_id=a),
        event(ToolCallDelta, 7, call_id=b, delta='"Friday"}'),
        event(ToolCallCompleted, 8, call_id=b),
        event(ResponseCompleted, 9),
    ]
    state = reduce_stream(events, InferenceRunId("r"))
    assert state.status is StreamStatus.COMPLETED
    assert [
        (call.call_id.value, call.tool_name, call.arguments.raw)
        for call in state.completed_tool_calls
    ] == [
        ("A", "weather", '{"city":"Paris"}'),
        ("B", "calendar", '{"day":"Friday"}'),
    ]
    assert state.text == "" and state.partial_tool_calls == ()


def test_p5_ac019_name_and_identity_preserved() -> None:
    call_id = ToolCallId("CaseSensitive")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(ToolCallStarted, 1, call_id=call_id, tool_name="lookup"),
            event(ToolCallDelta, 2, call_id=call_id, delta="  [\n"),
            event(ToolCallCompleted, 3, call_id=call_id),
            event(ResponseCompleted, 4),
        ],
        InferenceRunId("r"),
    )
    call = state.completed_tool_calls[0]
    assert call.call_id == call_id and call.tool_name == "lookup"
    assert call.arguments.raw == "  [\n"


def test_p5_ac020_duplicate_start_or_end_is_rejected() -> None:
    call_id = ToolCallId("A")
    state = reduce_event(StreamState(InferenceRunId("r")), event(ResponseStarted, 0))
    state = reduce_event(
        state, event(ToolCallStarted, 1, call_id=call_id, tool_name="tool")
    )
    with pytest.raises(StreamToolCallError, match="already used"):
        reduce_event(state, event(ToolCallStarted, 2, call_id=call_id, tool_name="tool"))
    state = reduce_event(state, event(ToolCallCompleted, 2, call_id=call_id))
    with pytest.raises(StreamToolCallError, match="not open"):
        reduce_event(state, event(ToolCallCompleted, 3, call_id=call_id))


def test_p5_ac021_fragment_after_close_rejected() -> None:
    call_id = ToolCallId("A")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(ToolCallStarted, 1, call_id=call_id, tool_name="tool"),
            event(ToolCallCompleted, 2, call_id=call_id),
        ],
        InferenceRunId("r"),
    )
    with pytest.raises(Exception, match="incomplete"):
        reduce_event(state, event(ToolCallDelta, 3, call_id=call_id, delta="late"))
    state = reduce_event(StreamState(InferenceRunId("r")), event(ResponseStarted, 0))
    state = reduce_event(
        state, event(ToolCallStarted, 1, call_id=call_id, tool_name="tool")
    )
    state = reduce_event(state, event(ToolCallCompleted, 2, call_id=call_id))
    with pytest.raises(StreamToolCallError, match="not open"):
        reduce_event(state, event(ToolCallDelta, 3, call_id=call_id, delta="late"))


def test_p5_ac022_raw_never_automatically_parsed_or_marked_valid() -> None:
    call_id = ToolCallId("A")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(ToolCallStarted, 1, call_id=call_id, tool_name="tool"),
            event(ToolCallDelta, 2, call_id=call_id, delta="not {valid JSON"),
            event(ToolCallCompleted, 3, call_id=call_id),
            event(ResponseCompleted, 4),
        ],
        InferenceRunId("r"),
    )
    call = state.completed_tool_calls[0]
    assert isinstance(call, ToolCall)
    assert call.arguments.raw == "not {valid JSON"
    assert not call.arguments.has_parsed and call.arguments.parsed is None


def test_p5_ac023_never_execute_or_manufacture_tool_results() -> None:
    call_id = ToolCallId("A")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(ToolCallStarted, 1, call_id=call_id, tool_name="tool"),
            event(ToolCallDelta, 2, call_id=call_id, delta="SECRET"),
            event(ResponseFailed, 3, reason_code="transport_failed"),
        ],
        InferenceRunId("r"),
    )
    assert not state.completed_tool_calls
    assert state.partial_tool_calls[0].raw == "SECRET"
    assert "SECRET" not in repr(state)
    assert not hasattr(state, "tool_results")


def test_p5_ac024_raw_size_budget_and_immutability() -> None:
    call_id = ToolCallId("A")
    state = reduce_event(StreamState(InferenceRunId("r")), event(ResponseStarted, 0))
    state = reduce_event(
        state, event(ToolCallStarted, 1, call_id=call_id, tool_name="tool")
    )
    state = reduce_event(
        state, event(ToolCallDelta, 2, call_id=call_id, delta="x" * 1_048_576)
    )
    with pytest.raises(StreamLimitError) as error:
        reduce_event(state, event(ToolCallDelta, 3, call_id=call_id, delta="SECRET"))
    assert "SECRET" not in str(error.value)
    assert state.partial_tool_calls[0].size_bytes == 1_048_576
    with pytest.raises(FrozenInstanceError):
        state.partial_tool_calls[0].closed = True  # type: ignore[misc]


def test_empty_call_is_raw_empty_and_never_parsed() -> None:
    call_id = ToolCallId("A")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(ToolCallStarted, 1, call_id=call_id, tool_name="noop"),
            event(ToolCallCompleted, 2, call_id=call_id),
            event(ResponseCompleted, 3),
        ],
        InferenceRunId("r"),
    )
    assert state.completed_tool_calls[0].arguments.raw == ""
    assert state.completed_tool_calls[0].arguments.has_parsed is False


def test_text_and_tool_arguments_are_separate() -> None:
    call_id = ToolCallId("A")
    state = reduce_stream(
        [
            event(ResponseStarted, 0),
            event(TextDelta, 1, delta="Hello"),
            event(ToolCallStarted, 2, call_id=call_id, tool_name="lookup"),
            event(ToolCallDelta, 3, call_id=call_id, delta="SECRET"),
            event(ToolCallCompleted, 4, call_id=call_id),
            event(ResponseCompleted, 5),
        ],
        InferenceRunId("r"),
    )
    assert state.text == "Hello"
    assert state.completed_tool_calls[0].arguments.raw == "SECRET"
    assert "SECRET" not in repr(state.completed_tool_calls[0])
