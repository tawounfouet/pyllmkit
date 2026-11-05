"""P5-AC-009..016: deterministic ordering, lifecycle and text reconstruction."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    ResponseCancelled,
    ResponseCompleted,
    ResponseFailed,
    ResponseStarted,
    StreamDuplicateSequence,
    StreamLifecycleError,
    StreamLimitError,
    StreamOutOfOrder,
    StreamRunMismatch,
    StreamSequenceGap,
    StreamState,
    StreamStatus,
    StreamToolCallError,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    UsageUpdated,
    observe_eof,
    reduce_event,
    reduce_stream,
)
from pyllmkit.domain.tooling import ToolCallId


def rid() -> InferenceRunId:
    return InferenceRunId("p5-run")


def start() -> ResponseStarted:
    return ResponseStarted(run_id=rid(), sequence=0)


def test_p5_ac009_start_first_unique() -> None:
    with pytest.raises(StreamLifecycleError, match="begin"):
        reduce_event(StreamState(rid()), TextDelta(run_id=rid(), sequence=0, delta="x"))
    state = reduce_event(StreamState(rid()), start())
    assert state.status is StreamStatus.STARTED
    with pytest.raises(StreamLifecycleError, match="duplicate ResponseStarted"):
        reduce_event(state, ResponseStarted(run_id=rid(), sequence=1))


def test_p5_ac010_text_reducer_deterministic_and_immutable() -> None:
    events = [
        start(),
        TextDelta(run_id=rid(), sequence=1, delta="Bon"),
        TextDelta(run_id=rid(), sequence=2, delta="jour 💙"),
        ResponseCompleted(run_id=rid(), sequence=3),
    ]
    first = reduce_stream(events, rid())
    assert first == reduce_stream(events, rid())
    assert first.text == "Bonjour 💙"
    assert first.last_sequence == 3 and first.is_complete
    assert "Bonjour" not in repr(first)
    with pytest.raises(FrozenInstanceError):
        first.next_sequence = 0  # type: ignore[misc]


def test_p5_ac011_duplicate_sequence_rejected() -> None:
    state = reduce_event(StreamState(rid()), start())
    with pytest.raises(StreamDuplicateSequence):
        reduce_event(state, start())


def test_p5_ac012_gap_and_out_of_order() -> None:
    state = reduce_event(StreamState(rid()), start())
    with pytest.raises(StreamSequenceGap):
        reduce_event(state, TextDelta(run_id=rid(), sequence=3, delta="x"))
    state = reduce_event(state, TextDelta(run_id=rid(), sequence=1, delta="A"))
    state = reduce_event(state, TextDelta(run_id=rid(), sequence=2, delta="B"))
    with pytest.raises(StreamOutOfOrder):
        reduce_event(state, TextDelta(run_id=rid(), sequence=0, delta="late"))


def test_p5_ac013_run_id_is_exact() -> None:
    state = reduce_event(StreamState(rid()), start())
    with pytest.raises(StreamRunMismatch):
        reduce_event(state, TextDelta(run_id=InferenceRunId("other"), sequence=1, delta="x"))


def test_p5_ac014_terminality_is_exclusive() -> None:
    for terminal, expected in (
        (ResponseCompleted(run_id=rid(), sequence=1), StreamStatus.COMPLETED),
        (ResponseFailed(run_id=rid(), sequence=1, reason_code="timeout"), StreamStatus.FAILED),
        (ResponseCancelled(run_id=rid(), sequence=1), StreamStatus.CANCELLED),
    ):
        state = reduce_event(reduce_event(StreamState(rid()), start()), terminal)
        assert state.status is expected
        assert state.is_complete == (expected is StreamStatus.COMPLETED)
        with pytest.raises(StreamLifecycleError, match="terminal"):
            reduce_event(state, ResponseCompleted(run_id=rid(), sequence=2))


def test_p5_ac015_eof_never_implies_success() -> None:
    assert reduce_stream([], rid()).status is StreamStatus.INCOMPLETE
    partial = reduce_stream(
        [start(), TextDelta(run_id=rid(), sequence=1, delta="some")], rid()
    )
    assert partial.status is StreamStatus.INCOMPLETE
    assert partial.text == "some"
    with pytest.raises(StreamLifecycleError, match="incomplete"):
        reduce_event(partial, ResponseCompleted(run_id=rid(), sequence=2))
    completed = reduce_stream([start(), ResponseCompleted(run_id=rid(), sequence=1)], rid())
    assert observe_eof(completed) == completed


def test_p5_ac016_tool_fragments_never_added_to_text() -> None:
    call = ToolCallId("call-a")
    events = [
        start(),
        TextDelta(run_id=rid(), sequence=1, delta="Hello "),
        ToolCallStarted(run_id=rid(), sequence=2, call_id=call, tool_name="search"),
        ToolCallDelta(run_id=rid(), sequence=3, call_id=call, delta='{"secret":"no"}'),
        TextDelta(run_id=rid(), sequence=4, delta="world"),
        ToolCallCompleted(run_id=rid(), sequence=5, call_id=call),
        ResponseCompleted(run_id=rid(), sequence=6),
    ]
    state = reduce_stream(events, rid())
    assert state.text == "Hello world" and "secret" not in state.text


def test_unknown_duplicate_and_closed_tool_rejected() -> None:
    call = ToolCallId("A")
    state = reduce_event(StreamState(rid()), start())
    with pytest.raises(StreamToolCallError, match="not open"):
        reduce_event(state, ToolCallDelta(run_id=rid(), sequence=1, call_id=call, delta="x"))
    state = reduce_event(
        state, ToolCallStarted(run_id=rid(), sequence=1, call_id=call, tool_name="run")
    )
    with pytest.raises(StreamToolCallError, match="already used"):
        reduce_event(
            state, ToolCallStarted(run_id=rid(), sequence=2, call_id=call, tool_name="run")
        )
    with pytest.raises(StreamLifecycleError, match="open tool"):
        reduce_event(state, ResponseCompleted(run_id=rid(), sequence=2))
    state = reduce_event(state, ToolCallCompleted(run_id=rid(), sequence=2, call_id=call))
    with pytest.raises(StreamToolCallError, match="not open"):
        reduce_event(state, ToolCallCompleted(run_id=rid(), sequence=3, call_id=call))


def test_usage_final_no_invention() -> None:
    state = reduce_event(StreamState(rid()), start())
    state = reduce_event(state, UsageUpdated(run_id=rid(), sequence=1, usage=Usage(output_tokens=3)))
    assert state.usage is not None and state.usage.input_tokens is None
    assert not state.usage_final
    state = reduce_event(
        state, UsageUpdated(run_id=rid(), sequence=2, usage=Usage(output_tokens=4), is_final=True)
    )
    assert state.usage_final
    with pytest.raises(StreamLifecycleError, match="usage already"):
        reduce_event(state, UsageUpdated(run_id=rid(), sequence=3, usage=Usage()))


def test_text_budget_rejected_without_raw_in_exception() -> None:
    state = reduce_event(StreamState(rid()), start())
    for seq in range(1, 9):
        state = reduce_event(
            state, TextDelta(run_id=rid(), sequence=seq, delta="x" * 1_048_576)
        )
    with pytest.raises(StreamLimitError) as exc:
        reduce_event(state, TextDelta(run_id=rid(), sequence=9, delta="SECRET"))
    assert "SECRET" not in str(exc.value)


def test_tool_count_limit_rejected() -> None:
    state = reduce_event(StreamState(rid()), start())
    for seq in range(1, 129):
        state = reduce_event(
            state,
            ToolCallStarted(run_id=rid(), sequence=seq, call_id=ToolCallId(str(seq)), tool_name="tool"),
        )
    with pytest.raises(StreamLimitError, match="count budget"):
        reduce_event(
            state,
            ToolCallStarted(run_id=rid(), sequence=129, call_id=ToolCallId("extra"), tool_name="tool"),
        )


def test_event_budget_and_invalid_state() -> None:
    with pytest.raises(Exception, match="run_id"):
        StreamState(cast(InferenceRunId, "bad"))
    state = StreamState(rid(), status=StreamStatus.STARTED, next_sequence=100_000)
    with pytest.raises(StreamLimitError, match="event count"):
        reduce_event(state, TextDelta(run_id=rid(), sequence=100_000, delta="x"))


def test_failure_preserves_partial_without_implying_success() -> None:
    state = reduce_stream(
        [
            start(),
            TextDelta(run_id=rid(), sequence=1, delta="unfinished"),
            ResponseFailed(run_id=rid(), sequence=2, reason_code="transport_failed"),
        ],
        rid(),
    )
    assert state.status is StreamStatus.FAILED
    assert state.error_code == "transport_failed"
    assert state.text == "unfinished" and not state.is_complete
    assert "transport_failed" not in repr(state)
