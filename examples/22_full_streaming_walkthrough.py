"""P5 L5.6 - fully offline streaming domain walkthrough, including tool deltas."""

import asyncio
import json

from pyllmkit.domain.inference import InferenceRunId, Usage
from pyllmkit.domain.streaming import (
    MemoryAsyncInferenceStream,
    MemoryInferenceStream,
    ResponseCompleted,
    ResponseStarted,
    StreamEvent,
    TextDelta,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    UsageUpdated,
    consume_async_stream,
    consume_stream,
    stream_from_dict,
    stream_to_dict,
)
from pyllmkit.domain.tooling import ToolCallId


async def main() -> None:
    run_id = InferenceRunId("offline-full-p5")
    a, b = ToolCallId("weather-1"), ToolCallId("calendar-2")
    events: tuple[StreamEvent, ...] = (
        ResponseStarted(run_id=run_id, sequence=0),
        TextDelta(run_id=run_id, sequence=1, delta="Je consulte deux outils. "),
        ToolCallStarted(run_id=run_id, sequence=2, call_id=a, tool_name="weather"),
        ToolCallStarted(run_id=run_id, sequence=3, call_id=b, tool_name="calendar"),
        ToolCallDelta(run_id=run_id, sequence=4, call_id=a, delta='{"city":"'),
        ToolCallDelta(run_id=run_id, sequence=5, call_id=b, delta='{"date":"'),
        ToolCallDelta(run_id=run_id, sequence=6, call_id=a, delta='Paris"}'),
        ToolCallCompleted(run_id=run_id, sequence=7, call_id=a),
        ToolCallDelta(run_id=run_id, sequence=8, call_id=b, delta='2026-11-05"}'),
        ToolCallCompleted(run_id=run_id, sequence=9, call_id=b),
        TextDelta(run_id=run_id, sequence=10, delta="Aucun outil n'a ete execute."),
        UsageUpdated(
            run_id=run_id,
            sequence=11,
            usage=Usage(output_tokens=12),
            is_final=False,
        ),
        ResponseCompleted(run_id=run_id, sequence=12),
    )
    sync_state = consume_stream(MemoryInferenceStream(run_id, events))
    async_state = await consume_async_stream(MemoryAsyncInferenceStream(run_id, events))
    assert sync_state == async_state and sync_state.is_complete
    assert len(sync_state.completed_tool_calls) == 2
    assert all(not call.arguments.has_parsed for call in sync_state.completed_tool_calls)
    data = stream_to_dict(events, run_id)
    restored_id, restored_events = stream_from_dict(json.loads(json.dumps(data)))
    assert restored_id == run_id and restored_events == events
    assert data["observed_status"] == "completed"
    assert sync_state.usage is not None and sync_state.usage.input_tokens is None
    assert not sync_state.usage_final
    print("P5 streaming:", sync_state.text)
    print("Descriptive tool calls:", len(sync_state.completed_tool_calls))
    print("Sync, async, JSON v1: validated offline (no provider, no execution).")


if __name__ == "__main__":
    asyncio.run(main())
