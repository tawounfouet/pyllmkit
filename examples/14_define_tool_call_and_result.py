"""P4 L4.2 demonstration: describe calls and correlate results, without execution."""

from pyllmkit.domain.tooling import (
    Tool,
    ToolArguments,
    ToolCall,
    ToolCallId,
    ToolResult,
    ToolSchema,
    ValidationStatus,
    attach_tool_result,
    validate_tool_call,
)


def main() -> None:
    tool = Tool("get_weather", "Describe local weather", ToolSchema({
        "type": "object",
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
        "additionalProperties": False,
    }))
    first = ToolCall(
        ToolCallId("call-001"), "get_weather",
        ToolArguments(raw='{"city": "Paris"}', parsed={"city": "Paris"}),
    )
    second = ToolCall(
        ToolCallId("call-002"), "get_weather",
        ToolArguments(raw='{"city": "Lyon"}', parsed={"city": "Lyon"}),
    )
    assert validate_tool_call(first, (tool,)).status is ValidationStatus.VALID
    assert validate_tool_call(second, (tool,)).status is ValidationStatus.VALID
    all_calls = (first, second)
    attached = attach_tool_result(
        all_calls, (), ToolResult(first.call_id, {"temperature": 18}),
    )
    attached = attach_tool_result(
        all_calls, attached, ToolResult(second.call_id, {"code": "unavailable"}, is_error=True),
    )
    assert len(attached) == 2 and attached[1].is_error
    print("L4.2: two calls and correlated final results (no execution).")


if __name__ == "__main__":
    main()
