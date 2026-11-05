# Progressive tool-call reconstruction (P5 L5.3)

ToolCallStarted identifies a M4 ToolCallId and tool name. ToolCallDelta carries raw text belonging to exactly that ID. ToolCallCompleted marks that ID closed, and only then can StreamState.completed_tool_calls describe a M4 ToolCall containing ToolArguments(raw=...) and has_parsed=False.

Calls can be interleaved. Each ToolCallProgress uses immutable chunk nodes and an explicit per-call 1 MiB raw byte budget. Unknown IDs, duplicates, fragments after close and open calls at a successful terminal are rejected. FAILED and CANCELLED preserve partial tool progress without pretending it completed.

No tool handler is called. No ToolResult or parsed JSON or StructuredOutput VALID is manufactured. This is a provider-free domain-only representation. See ADR-033/034 and P5-AC-017..024.
