"""P5-AC-041..048: integrated streaming qualification and safeguards."""

import asyncio
import copy
import time
from pathlib import Path

import pytest

from pyllmkit import __version__
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    MemoryAsyncInferenceStream,
    MemoryInferenceStream,
    ResponseCancelled,
    ResponseCompleted,
    ResponseStarted,
    StreamEvent,
    StreamLifecycleError,
    StreamStatus,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    UsageUpdated,
    consume_async_stream,
    consume_stream,
    event_from_dict,
    event_to_dict,
    reduce_stream,
    stream_from_dict,
    stream_to_dict,
)
from pyllmkit.domain.streaming.reconstruction import MAX_EVENTS
from pyllmkit.domain.tooling import ToolCallId

ROOT = Path(__file__).resolve().parents[2]


def sample() -> tuple[InferenceRunId, tuple[StreamEvent, ...]]:
    rid = InferenceRunId("end-to-end-p5")
    c = ToolCallId("tool-A")
    return rid, (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="Bonjour "),
        ToolCallStarted(run_id=rid, sequence=2, call_id=c, tool_name="lookup"),
        ToolCallDelta(run_id=rid, sequence=3, call_id=c, delta='{"x":'),
        ToolCallDelta(run_id=rid, sequence=4, call_id=c, delta='"Paris"}'),
        ToolCallCompleted(run_id=rid, sequence=5, call_id=c),
        TextDelta(run_id=rid, sequence=6, delta="le monde"),
        UsageUpdated(run_id=rid, sequence=7, usage=Usage(output_tokens=7)),
        ResponseCompleted(run_id=rid, sequence=8),
    )


def test_p5_ac041_full_sync_async_text_parity() -> None:
    rid, events = sample()
    synchronous = consume_stream(MemoryInferenceStream(rid, events))
    asynchronous = asyncio.run(consume_async_stream(MemoryAsyncInferenceStream(rid, events)))
    assert synchronous == asynchronous
    assert synchronous.text == "Bonjour le monde"
    assert synchronous.status is StreamStatus.COMPLETED


def test_p5_ac042_full_codec_roundtrip_preserves_tool_calls() -> None:
    rid, events = sample()
    original = reduce_stream(events, rid)
    encoded = stream_to_dict(events, rid)
    new_run, restored_events = stream_from_dict(encoded)
    restored = reduce_stream(restored_events, new_run)
    assert restored.completed_tool_calls == original.completed_tool_calls
    tool = restored.completed_tool_calls[0]
    assert tool.call_id.value == "tool-A"
    assert tool.arguments.raw == '{"x":"Paris"}'
    assert not tool.arguments.has_parsed
    assert restored.text == original.text


def test_p5_ac043_failure_cancel_and_post_terminal_guards() -> None:
    rid = InferenceRunId("cancelled-case")
    events: tuple[StreamEvent, ...] = (
        ResponseStarted(run_id=rid, sequence=0),
        TextDelta(run_id=rid, sequence=1, delta="partial"),
        ResponseCancelled(run_id=rid, sequence=2),
    )
    encoded = stream_to_dict(events, rid)
    assert encoded["observed_status"] == "cancelled"
    assert stream_from_dict(encoded) == (rid, events)
    with pytest.raises(StreamLifecycleError):
        reduce_stream(events + (TextDelta(run_id=rid, sequence=3, delta="late"),), rid)
    damaged = copy.deepcopy(encoded)
    damaged["observed_status"] = "completed"
    with pytest.raises(DomainValidationError):
        stream_from_dict(damaged)


def test_p5_ac044_old_m1_m2_m3_m4_codecs_round_trip() -> None:
    from pyllmkit.domain import (
        Content,
        InferenceRequest,
        Message,
        ModelId,
        ModelTarget,
        Role,
        TextContent,
        message_from_dict,
        message_to_dict,
        request_from_dict,
        request_to_dict,
    )
    from pyllmkit.domain.models import Model, ModelFamily, ModelIdentity, model_from_dict, model_to_dict
    from pyllmkit.domain.tooling import Tool, ToolSchema
    from pyllmkit.domain.tooling.serialization import tooling_from_dict, tooling_to_dict

    model = Model(ModelId("p5/sample"), ModelIdentity(ModelFamily("sample")))
    assert model_to_dict(model_from_dict(model_to_dict(model))) == model_to_dict(model)
    msg = Message(Role.USER, Content((TextContent("x"),)))
    assert message_from_dict(message_to_dict(msg)) == msg
    request = InferenceRequest(ModelTarget(ModelId("m")), (msg,))
    assert request_from_dict(request_to_dict(request)) == request
    tool = Tool("lookup", None, ToolSchema({"type": "object"}))
    assert tooling_to_dict(tooling_from_dict(tooling_to_dict(tool))) == tooling_to_dict(tool)


def test_p5_ac045_offline_and_documents_are_integrated() -> None:
    from tests.architecture.guard import forbidden_imports

    streaming = ROOT / "src/pyllmkit/domain/streaming"
    for module in streaming.glob("*.py"):
        assert forbidden_imports(module) == []
    for document in (
        ROOT / "docs/api/streaming.md",
        ROOT / "docs/architecture/STREAMING_JSON_SCHEMA_V1.md",
        ROOT / "docs/quality/PHASE_5_TRACEABILITY.md",
        ROOT / "docs/architecture/PHASE_5_STREAMING_ARCHITECTURE.md",
    ):
        assert document.is_file()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Phase 5 - Streaming" in readme


def test_p5_ac046_reject_oversized_decoded_trace_before_replay() -> None:
    rid = InferenceRunId("max-trace")
    basic = event_to_dict(ResponseStarted(run_id=rid, sequence=0))
    incoming = {
        "schema_version": 1,
        "object_type": "stream_trace",
        "run_id": rid.value,
        "events": [basic] * (MAX_EVENTS + 1),
        "observed_status": "completed",
    }
    with pytest.raises(DomainValidationError, match="event count exceeded"):
        stream_from_dict(incoming)
    assert event_from_dict(basic) == ResponseStarted(run_id=rid, sequence=0)


def test_p5_ac047_ten_thousand_event_replay_has_bounded_time() -> None:
    rid = InferenceRunId("load-test")
    events: list[StreamEvent] = [ResponseStarted(run_id=rid, sequence=0)]
    events.extend(
        TextDelta(run_id=rid, sequence=i, delta="abc") for i in range(1, 10_001)
    )
    events.append(ResponseCompleted(run_id=rid, sequence=10_001))
    start = time.perf_counter()
    result = reduce_stream(events, rid)
    elapsed = time.perf_counter() - start
    assert result.is_complete
    assert len(result.text) == 30_000
    assert elapsed < 15.0  # generous CI guard; not a provider/network benchmark


def test_p5_ac048_packaging_public_api_and_no_release_claim() -> None:
    from pyllmkit.domain.streaming import (
        STREAMING_SCHEMA_VERSION,
        AsyncInferenceStream,
        InferenceStream,
        StreamState,
        consume_stream,
    )

    assert __version__ == "0.1.0a2"
    assert STREAMING_SCHEMA_VERSION == 1
    assert callable(consume_stream)
    assert hasattr(AsyncInferenceStream, "__aiter__")
    assert hasattr(InferenceStream, "__iter__")
    assert StreamState(InferenceRunId("smoke")).status is StreamStatus.CREATED
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0a2"' in project
    assert "dependencies = []" in project
    for index in range(18, 23):
        matches = tuple((ROOT / "examples").glob(f"{index:02}_*.py"))
        assert len(matches) == 1


def test_invalid_trace_decoder_does_not_echo_secret() -> None:
    rid = InferenceRunId("test")
    payload = stream_to_dict(
        (
            ResponseStarted(run_id=rid, sequence=0),
            TextDelta(run_id=rid, sequence=1, delta="SECRET-ARGUMENT"),
        ),
        rid,
    )
    payload["observed_status"] = "completed"
    with pytest.raises(DomainValidationError) as error:
        stream_from_dict(payload)
    assert "SECRET-ARGUMENT" not in str(error.value)
