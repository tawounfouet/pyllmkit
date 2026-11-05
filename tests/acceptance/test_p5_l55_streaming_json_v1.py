"""P5-AC-033..040: strict independent Streaming JSON v1 round trips."""

import copy
import json
from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import FinishReason, FinishReasonCode, InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    STREAMING_SCHEMA_VERSION,
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
    event_from_dict,
    event_to_dict,
    stream_from_dict,
    stream_to_dict,
)
from pyllmkit.domain.tooling import ToolCallId


def rid() -> InferenceRunId:
    return InferenceRunId("codec-stream")


def all_event_types() -> tuple[StreamEvent, ...]:
    call_id = ToolCallId("id-1")
    return (
        ResponseStarted(run_id=rid(), sequence=0),
        TextDelta(run_id=rid(), sequence=1, delta="secret\n🙂"),
        ToolCallStarted(run_id=rid(), sequence=2, call_id=call_id, tool_name="tool"),
        ToolCallDelta(run_id=rid(), sequence=3, call_id=call_id, delta='{"x":'),
        ToolCallCompleted(run_id=rid(), sequence=4, call_id=call_id),
        UsageUpdated(run_id=rid(), sequence=5, usage=Usage(output_tokens=5), is_final=True),
        ResponseCompleted(
            run_id=rid(), sequence=6,
            finish_reason=FinishReason(FinishReasonCode.STOP, "native_stop"),
        ),
        ResponseFailed(run_id=rid(), sequence=7, reason_code="network_failure"),
        ResponseCancelled(run_id=rid(), sequence=8, reason_code="manual_cancel"),
    )


def test_p5_ac033_every_event_round_trips_through_json_data() -> None:
    assert STREAMING_SCHEMA_VERSION == 1
    for value in all_event_types():
        encoded = event_to_dict(value)
        after_text = json.loads(json.dumps(encoded, ensure_ascii=False))
        reconstructed = event_from_dict(after_text)
        assert reconstructed == value
        assert event_to_dict(reconstructed) == encoded


def test_p5_ac034_trace_round_trip_and_exact_order() -> None:
    values = tuple(all_event_types()[:7])
    payload = stream_to_dict(values, rid())
    assert payload["observed_status"] == "completed"
    run_id, events = stream_from_dict(json.loads(json.dumps(payload)))
    assert run_id == rid() and events == values
    assert stream_to_dict(events, run_id) == payload


def test_p5_ac035_unknown_versions_types_kinds_and_fields_rejected() -> None:
    base = event_to_dict(ResponseStarted(run_id=rid(), sequence=0))
    cases: list[dict[str, object]] = []
    for variant in (2, "1", True):
        altered = copy.deepcopy(base)
        altered["schema_version"] = variant
        cases.append(altered)
    for key, value in (
        ("object_type", "tool_call"),
        ("kind", "unrecognized"),
        ("sequence", True),
        ("sequence", "0"),
        ("run_id", None),
    ):
        altered = copy.deepcopy(base)
        altered[key] = value
        cases.append(altered)
    altered = copy.deepcopy(base)
    altered["unexpected"] = "x"
    cases.append(altered)
    altered = copy.deepcopy(base)
    altered.pop("kind")
    cases.append(altered)
    altered = copy.deepcopy(base)
    altered["payload"] = {"unknown": "x"}
    cases.append(altered)
    for case in cases:
        with pytest.raises(DomainValidationError):
            event_from_dict(case)


def test_p5_ac036_wrong_payload_and_usage_types_rejected() -> None:
    source = event_to_dict(all_event_types()[5])
    altered = copy.deepcopy(source)
    cast(dict[str, object], altered["payload"])["is_final"] = 1
    with pytest.raises(DomainValidationError):
        event_from_dict(altered)
    altered = copy.deepcopy(source)
    raw_usage = cast(dict[str, object], cast(dict[str, object], altered["payload"])["usage"])
    raw_usage["output_tokens"] = True
    with pytest.raises(DomainValidationError):
        event_from_dict(altered)
    altered = copy.deepcopy(source)
    raw_usage = cast(dict[str, object], cast(dict[str, object], altered["payload"])["usage"])
    raw_usage.pop("input_tokens")
    with pytest.raises(DomainValidationError):
        event_from_dict(altered)
    altered = copy.deepcopy(source)
    raw_usage = cast(dict[str, object], cast(dict[str, object], altered["payload"])["usage"])
    raw_usage["total_tokens"] = -2
    with pytest.raises(DomainValidationError):
        event_from_dict(altered)


def test_p5_ac037_forged_completed_trace_rejected() -> None:
    partial = stream_to_dict(all_event_types()[:2], rid())
    assert partial["observed_status"] == "incomplete"
    forged = copy.deepcopy(partial)
    forged["observed_status"] = "completed"
    with pytest.raises(DomainValidationError, match="mismatches replay"):
        stream_from_dict(forged)


def test_p5_ac038_partial_failed_cancelled_distinct() -> None:
    prefix = all_event_types()[:2]
    for terminal, expected in (
        (ResponseFailed(run_id=rid(), sequence=2, reason_code="oops"), "failed"),
        (ResponseCancelled(run_id=rid(), sequence=2), "cancelled"),
    ):
        events = (*prefix, terminal)
        encoded = stream_to_dict(events, rid())
        assert encoded["observed_status"] == expected
        assert stream_from_dict(json.loads(json.dumps(encoded))) == (rid(), events)
    partial = stream_to_dict(prefix, rid())
    assert partial["observed_status"] == "incomplete"


def test_p5_ac039_forged_run_sequence_and_terminal_invalid() -> None:
    values = all_event_types()[:2]
    encoded = stream_to_dict(values, rid())
    corrupted = copy.deepcopy(encoded)
    cast(dict[str, object], cast(list[object], corrupted["events"])[1])["run_id"] = "other"
    with pytest.raises(DomainValidationError):
        stream_from_dict(corrupted)
    corrupted = copy.deepcopy(encoded)
    cast(dict[str, object], cast(list[object], corrupted["events"])[1])["sequence"] = 3
    with pytest.raises(DomainValidationError):
        stream_from_dict(corrupted)
    corrupted = copy.deepcopy(encoded)
    corrupted["events"] = "not-list"
    with pytest.raises(DomainValidationError):
        stream_from_dict(corrupted)
    corrupted = copy.deepcopy(encoded)
    corrupted["schema_version"] = True
    with pytest.raises(DomainValidationError):
        stream_from_dict(corrupted)


def test_p5_ac040_text_opaque_and_legacy_codecs_untouched() -> None:
    from pyllmkit.domain.inference.serialization import INFERENCE_SCHEMA_VERSION
    from pyllmkit.domain.interactions.serialization import INTERACTION_SCHEMA_VERSION
    from pyllmkit.domain.models.serialization import SCHEMA_VERSION
    from pyllmkit.domain.tooling.serialization import TOOLING_SCHEMA_VERSION

    assert (INFERENCE_SCHEMA_VERSION, INTERACTION_SCHEMA_VERSION, SCHEMA_VERSION) == (1, 1, 1)
    assert TOOLING_SCHEMA_VERSION == STREAMING_SCHEMA_VERSION == 1
    text = TextDelta(run_id=rid(), sequence=1, delta='  {"not": "parsed"}  ')
    assert event_from_dict(event_to_dict(text)).delta == text.delta


def test_invalid_finish_and_tool_fields() -> None:
    bad = event_to_dict(all_event_types()[6])
    cast(dict[str, object], bad["payload"])["finish_reason"] = {
        "code": "invalid",
        "native_reason": None,
    }
    with pytest.raises(DomainValidationError):
        event_from_dict(bad)
    tool = event_to_dict(all_event_types()[2])
    cast(dict[str, object], tool["payload"])["tool_name"] = 19
    with pytest.raises(DomainValidationError):
        event_from_dict(tool)
    trace = stream_to_dict((), rid())
    assert trace["observed_status"] == "incomplete"
    with pytest.raises(DomainValidationError):
        stream_to_dict(cast(tuple[StreamEvent, ...], ("bad",)), rid())
