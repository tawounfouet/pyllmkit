"""P5-AC-001..008: typed, immutable, offline streaming event model."""

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import FinishReason, FinishReasonCode, InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    InferenceStream,
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
from pyllmkit.domain.tooling import ToolCallId


@pytest.fixture
def run_id() -> InferenceRunId:
    return InferenceRunId("run-p5")


def test_p5_ac001_inference_stream_is_behavioral_protocol(run_id: InferenceRunId) -> None:
    class MemoryStream:
        def __init__(self, rid: InferenceRunId) -> None:
            self._rid = rid

        @property
        def run_id(self) -> InferenceRunId:
            return self._rid

        def __iter__(self) -> Iterator[StreamEvent]:
            yield ResponseStarted(run_id=self._rid, sequence=0)

    def consume(stream: InferenceStream) -> tuple[StreamEvent, ...]:
        return tuple(stream)

    stream = MemoryStream(run_id)
    assert consume(stream) == (ResponseStarted(run_id=run_id, sequence=0),)
    assert not hasattr(stream, "invoke")


def test_p5_ac002_all_required_kinds_and_run_correlation(run_id: InferenceRunId) -> None:
    call_id = ToolCallId("call-1")
    values = (
        ResponseStarted(run_id=run_id, sequence=0),
        TextDelta(run_id=run_id, sequence=1, delta="x"),
        ToolCallStarted(run_id=run_id, sequence=2, call_id=call_id, tool_name="search"),
        ToolCallDelta(run_id=run_id, sequence=3, call_id=call_id, delta="{"),
        ToolCallCompleted(run_id=run_id, sequence=4, call_id=call_id),
        UsageUpdated(run_id=run_id, sequence=5, usage=Usage()),
        ResponseCompleted(run_id=run_id, sequence=6),
        ResponseFailed(run_id=run_id, sequence=7, reason_code="timeout"),
        ResponseCancelled(run_id=run_id, sequence=8),
    )
    assert len({value.kind for value in values}) == 9
    assert all(type(value.run_id) is InferenceRunId for value in values)
    assert [value.sequence for value in values] == list(range(9))


def test_p5_ac003_delta_is_literal_and_sensitive_reprs_are_redacted(
    run_id: InferenceRunId,
) -> None:
    raw = " secret\né💙  "
    delta = TextDelta(run_id=run_id, sequence=1, delta=raw)
    tool = ToolCallDelta(run_id=run_id, sequence=2, call_id=ToolCallId("c"), delta=raw)
    assert delta.delta == tool.delta == raw
    assert raw not in repr(delta) and raw not in repr(tool)


def test_p5_ac004_values_are_immutable(run_id: InferenceRunId) -> None:
    value = TextDelta(run_id=run_id, sequence=1, delta="yes")
    with pytest.raises(FrozenInstanceError):
        value.delta = "no"  # type: ignore[misc]
    assert value.delta == "yes"


def test_p5_ac005_tool_deltas_are_typed(run_id: InferenceRunId) -> None:
    call = ToolCallId("id")
    start = ToolCallStarted(run_id=run_id, sequence=1, call_id=call, tool_name="tool")
    delta = ToolCallDelta(run_id=run_id, sequence=2, call_id=call, delta="{}")
    end = ToolCallCompleted(run_id=run_id, sequence=3, call_id=call)
    assert start.call_id == delta.call_id == end.call_id
    assert delta.kind == "tool_call_delta"
    assert not hasattr(delta, "execute")


def test_p5_ac006_terminals_are_distinct(run_id: InferenceRunId) -> None:
    complete = ResponseCompleted(run_id=run_id, sequence=1, finish_reason=FinishReason(FinishReasonCode.STOP))
    failed = ResponseFailed(run_id=run_id, sequence=1, reason_code="transport_error")
    cancelled = ResponseCancelled(run_id=run_id, sequence=1)
    assert len({complete.kind, failed.kind, cancelled.kind}) == 3
    assert complete.finish_reason is not None
    assert cancelled.reason_code == "cancelled"


@pytest.mark.parametrize("bad", [-1, True, 2**63, 1.0, "1", None])
def test_p5_ac007_reject_invalid_sequence(run_id: InferenceRunId, bad: object) -> None:
    with pytest.raises(DomainValidationError, match="sequence"):
        ResponseStarted(run_id=run_id, sequence=cast(int, bad))


@pytest.mark.parametrize("bad", ["", " ", "c" * 65, "api secret!", "échec", "line\nbreak", 17])
def test_p5_ac007_reject_invalid_reason_code(run_id: InferenceRunId, bad: object) -> None:
    with pytest.raises(DomainValidationError, match="reason_code"):
        ResponseFailed(run_id=run_id, sequence=1, reason_code=cast(str, bad))


def test_p5_ac007_reject_abstract_and_wrong_run_id(run_id: InferenceRunId) -> None:
    with pytest.raises(DomainValidationError, match="abstract"):
        StreamEvent(run_id=run_id, sequence=0)
    with pytest.raises(DomainValidationError, match="run_id"):
        ResponseStarted(run_id=cast(InferenceRunId, "r"), sequence=0)


def test_p5_ac007_reject_invalid_delta_types_and_bytes(run_id: InferenceRunId) -> None:
    with pytest.raises(DomainValidationError, match="TextDelta.delta"):
        TextDelta(run_id=run_id, sequence=1, delta=cast(str, None))
    with pytest.raises(DomainValidationError, match="size limit"):
        TextDelta(run_id=run_id, sequence=1, delta="a" * 1_048_577)
    with pytest.raises(DomainValidationError, match="ToolCallDelta.delta"):
        ToolCallDelta(run_id=run_id, sequence=2, call_id=ToolCallId("c"), delta=cast(str, 12))
    with pytest.raises(DomainValidationError, match="size limit"):
        ToolCallDelta(run_id=run_id, sequence=2, call_id=ToolCallId("c"), delta="x" * 1_048_577)


def test_p5_ac007_reject_invalid_tool_fields(run_id: InferenceRunId) -> None:
    with pytest.raises(DomainValidationError, match="call_id"):
        ToolCallStarted(run_id=run_id, sequence=1, call_id=cast(ToolCallId, "c"), tool_name="x")
    with pytest.raises(DomainValidationError, match="Tool.name"):
        ToolCallStarted(run_id=run_id, sequence=1, call_id=ToolCallId("c"), tool_name="bad-name")
    with pytest.raises(DomainValidationError, match="call_id"):
        ToolCallDelta(run_id=run_id, sequence=1, call_id=cast(ToolCallId, None), delta="x")
    with pytest.raises(DomainValidationError, match="call_id"):
        ToolCallCompleted(run_id=run_id, sequence=1, call_id=cast(ToolCallId, "x"))


def test_p5_ac007_reject_invalid_usage_and_finish(run_id: InferenceRunId) -> None:
    with pytest.raises(DomainValidationError, match="UsageUpdated.usage"):
        UsageUpdated(run_id=run_id, sequence=1, usage=cast(Usage, None))
    with pytest.raises(DomainValidationError, match="is_final"):
        UsageUpdated(run_id=run_id, sequence=1, usage=Usage(), is_final=cast(bool, 1))
    with pytest.raises(DomainValidationError, match="finish_reason"):
        ResponseCompleted(run_id=run_id, sequence=1, finish_reason=cast(FinishReason, "x"))


def test_p5_ac008_offline_source_does_not_import_provider_io_or_executor() -> None:
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src/pyllmkit/domain/streaming"
    assert {"__init__.py", "events.py", "protocols.py"} <= {p.name for p in root.glob("*.py")}
    banned = {"os", "socket", "subprocess", "requests", "httpx", "openai", "anthropic", "asyncio"}
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            n.names[0].name.split(".")[0]
            for n in ast.walk(tree) if isinstance(n, ast.Import)
        } | {
            (n.module or "").split(".")[0]
            for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
        }
        assert not (banned & imported)
