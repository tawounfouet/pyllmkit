"""Provider-agnostic tooling domain, P4 L4.1 and L4.2."""

from .arguments import ToolArguments
from .calls import ToolCall, ToolResult
from .choice import ToolChoice, ToolChoiceKind, validate_tool_choice
from .definitions import Tool, validate_tool_set
from .identifiers import ToolCallId
from .schema import ToolSchema
from .validation import (
    ToolCallValidation,
    ValidationStatus,
    attach_tool_result,
    validate_tool_call,
)

__all__ = [
    "Tool",
    "ToolArguments",
    "ToolCall",
    "ToolCallId",
    "ToolCallValidation",
    "ToolChoice",
    "ToolChoiceKind",
    "ToolResult",
    "ToolSchema",
    "ValidationStatus",
    "attach_tool_result",
    "validate_tool_call",
    "validate_tool_choice",
    "validate_tool_set",
]
