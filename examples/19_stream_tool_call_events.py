"""L5.3: two interleaved tool calls are reconstructed without execution."""

from pyllmkit.domain.inference import InferenceRunId
from pyllmkit.domain.streaming import (
    ResponseCompleted,
    ResponseStarted,
    ToolCallCompleted,
    ToolCallDelta,
    ToolCallStarted,
    reduce_stream,
)
from pyllmkit.domain.tooling import ToolCallId


def main() -> None:
    run_id = InferenceRunId("offline-tool-stream")
    a, b = ToolCallId("call-A"), ToolCallId("call-B")
    events = (
        ResponseStarted(run_id=run_id, sequence=0),
        ToolCallStarted(run_id=run_id, sequence=1, call_id=a, tool_name="weather"),
        ToolCallStarted(run_id=run_id, sequence=2, call_id=b, tool_name="calendar"),
        ToolCallDelta(run_id=run_id, sequence=3, call_id=a, delta='{"city":"'),
        ToolCallDelta(run_id=run_id, sequence=4, call_id=b, delta='{"date":"'),
        ToolCallDelta(run_id=run_id, sequence=5, call_id=a, delta='Paris"}'),
        ToolCallCompleted(run_id=run_id, sequence=6, call_id=a),
        ToolCallDelta(run_id=run_id, sequence=7, call_id=b, delta='2026-11-05"}'),
        ToolCallCompleted(run_id=run_id, sequence=8, call_id=b),
        ResponseCompleted(run_id=run_id, sequence=9),
    )
    state = reduce_stream(events, run_id)
    for call in state.completed_tool_calls:
        print(call.tool_name, call.arguments.raw, "has_parsed", call.arguments.has_parsed)
    print("No tool execution or ToolResult was performed.")


if __name__ == "__main__":
    main()
