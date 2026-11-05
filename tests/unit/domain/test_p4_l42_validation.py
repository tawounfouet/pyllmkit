"""Negative tool-calling cases: immutability, semantic JSON profile and correlation."""

from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
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


def tool(schema: dict[str, object]) -> Tool:
    return Tool("t", None, ToolSchema(schema))


def evaluate(schema: dict[str, object], value: object) -> str | None:
    candidate = ToolCall(ToolCallId("id"), "t", ToolArguments(parsed=value))
    result = validate_tool_call(candidate, (tool(schema),))
    if result.status is ValidationStatus.VALID:
        return None
    assert result.status is ValidationStatus.INVALID
    return result.code


@pytest.mark.parametrize(("schema", "value", "error"), [
    ({"type": "number"}, True, "type_mismatch"),
    ({"type": "integer"}, 2.5, "type_mismatch"),
    ({"type": "integer"}, 2.0, None),
    ({"type": "object", "required": ["name"]}, {}, "required_missing"),
    ({"type": "object", "additionalProperties": False}, {"extra": 1}, "additional_property"),
    ({"type": "array", "minItems": 2}, [1], "min_items"),
    ({"type": "array", "maxItems": 1}, [1, 2], "max_items"),
    ({"type": "string", "minLength": 2}, "x", "min_length"),
    ({"type": "string", "maxLength": 1}, "xx", "max_length"),
    ({"type": "number", "minimum": 1}, 0, "minimum"),
    ({"type": "number", "maximum": 5}, 6, "maximum"),
    ({"const": 1}, True, "const_mismatch"),
    ({"const": 1}, 1.0, None),
    ({"enum": [True, 2]}, 1, "enum_mismatch"),
    ({"enum": [{"a": 1}]}, {"a": 1.0}, None),
    ({"type": ["integer", "null"]}, None, None),
    ({"type": "object", "properties": {"x": {"type": "array", "items": {"type": "integer"}}}}, {"x": ["bad"]}, "type_mismatch"),
    ({"type": "string"}, "valid", None),
])
def test_schema_instance_semantics(schema: dict[str, object], value: object, error: str | None) -> None:
    assert evaluate(schema, value) == error


def test_mutable_parsed_arguments_cannot_change_after_construction() -> None:
    source: dict[str, object] = {"city": ["Paris"]}
    args = ToolArguments(raw="raw-secret", parsed=source)
    cast(list[str], source["city"]).append("Lyon")
    assert args.parsed == {"city": ["Paris"]}
    decoded = cast(dict[str, object], args.parsed)
    cast(list[str], decoded["city"]).clear()
    assert args.parsed == {"city": ["Paris"]}
    assert "raw-secret" not in repr(args)


def test_mutable_result_payload_is_copied_and_hidden() -> None:
    source = {"secret": ["x"]}
    result = ToolResult(ToolCallId("id"), source)
    source["secret"].append("y")
    assert result.value == {"secret": ["x"]}
    decoded = cast(dict[str, object], result.value)
    cast(list[str], decoded["secret"]).clear()
    assert result.value == {"secret": ["x"]}
    assert "secret" not in repr(result)


def test_invalid_types_and_non_finite_result() -> None:
    with pytest.raises(DomainValidationError, match="ToolCall.call_id"):
        ToolCall(cast(ToolCallId, "id"), "t", ToolArguments())
    with pytest.raises(DomainValidationError, match="ToolCall.arguments"):
        ToolCall(ToolCallId("id"), "t", cast(ToolArguments, None))
    with pytest.raises(DomainValidationError, match="ToolArguments.raw"):
        ToolArguments(raw=cast(str, 10))
    with pytest.raises(DomainValidationError, match="finite"):
        ToolResult(ToolCallId("id"), float("nan"))
    with pytest.raises(DomainValidationError, match="ToolResult.call_id"):
        ToolResult(cast(ToolCallId, "id"), {})
    with pytest.raises(DomainValidationError, match="not JSON-compatible"):
        ToolArguments(parsed=object())


def test_duplicate_calls_results_orphaned_results_and_type_guards() -> None:
    c = ToolCall(ToolCallId("same"), "t", ToolArguments())
    same_id = ToolCall(ToolCallId("same"), "t", ToolArguments(parsed={}))
    with pytest.raises(DomainValidationError, match="duplicate ToolCallId"):
        attach_tool_result((c, same_id), (), ToolResult(c.call_id, {}))
    with pytest.raises(DomainValidationError, match="orphaned"):
        attach_tool_result((c,), (ToolResult(ToolCallId("other"), {}),), ToolResult(c.call_id, {}))
    with pytest.raises(DomainValidationError, match="duplicate final"):
        attach_tool_result(
            (c,), (ToolResult(c.call_id, {}), ToolResult(c.call_id, {})),
            ToolResult(c.call_id, {}),
        )
    with pytest.raises(DomainValidationError, match="calls must"):
        attach_tool_result(cast(tuple[ToolCall, ...], []), (), ToolResult(c.call_id, {}))
    with pytest.raises(DomainValidationError, match="results must"):
        attach_tool_result((c,), cast(tuple[ToolResult, ...], []), ToolResult(c.call_id, {}))
    with pytest.raises(DomainValidationError, match="result must"):
        attach_tool_result((c,), (), cast(ToolResult, None))
    with pytest.raises(DomainValidationError, match="expects a ToolCall"):
        validate_tool_call(cast(ToolCall, {}), (tool({}),))
