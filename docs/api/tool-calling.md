# Tool Calling - Phase 4, lot L4.2

> Status: implementation PR (P4-G2 not qualified yet). Sources: ADR-022/023/024/025 and P4 plan.

## Domain concepts

- \`ToolCallId\` is a caller-supplied opaque identifier (exact str, nonblank, <= 256 chars), with no automatic UUID.
- \`ToolArguments(raw=?, parsed=?)\` stores a raw string separately from an immutable parsed JSON tree. Missing parsed and explicit JSON null are different (inspect \`has_parsed\`).
- \`ToolCall(call_id, tool_name, arguments)\` is an identity-based immutable Entity, not an executable command. Two calls with different IDs are different even when arguments coincide.
- \`ToolResult(call_id, value, is_error=False)\` is an immutable JSON-compatible observation, not the output of code executed in the framework.
- \`validate_tool_call\` returns proof of VALID, INVALID or UNKNOWN for the **parsed** argument value only. UNKNOWN means parsed absent; raw is never parsed automatically. Invalid schema instances return a bounded reason code, with no raw payload or secret embedded.
- \`attach_tool_result\` is pure: it returns a new tuple, verifies local call identity and rejects unknown or repeated final results.

## Example

```python
from pyllmkit.domain.tooling import (
    Tool, ToolSchema, ToolCallId, ToolArguments, ToolCall, ToolResult,
    ValidationStatus, validate_tool_call, attach_tool_result,
)

weather = Tool("get_weather", None, ToolSchema({
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"], "additionalProperties": False,
}))
call = ToolCall(
    ToolCallId("call-001"), "get_weather",
    ToolArguments(raw='{"city":"Paris"}', parsed={"city": "Paris"}),
)
assert validate_tool_call(call, (weather,)).status is ValidationStatus.VALID
observed = ToolResult(call.call_id, {"temperature": 18})
attached = attach_tool_result((call,), (), observed)
assert attached == (observed,)
```

No provider is called and no real weather is fetched. The result above is illustrative caller-provided data.

## Security and scope

No hidden JSON text parsing; no automatic tool execution; no resolver, credentials, network, agent runtime, or streaming deltas. Raw, parsed and result bodies are omitted from repr, and validation errors use fixed codes. JSON Schema validation follows the limited P4-JSON-1 profile. Tooling JSON v1 serialization and composition with M3 belong to L4.4, not L4.2.
