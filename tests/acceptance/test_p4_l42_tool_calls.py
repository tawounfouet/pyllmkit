"""P4-AC-009..016 acceptance tests for pure ToolCall and ToolResult domain."""

from typing import cast

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.tooling import (
    Tool,
    ToolArguments,
    ToolCall,
    ToolCallId,
    ToolCallValidation,
    ToolResult,
    ToolSchema,
    ValidationStatus,
    attach_tool_result,
    validate_tool_call,
)


def tool() -> Tool:
    return Tool("get_weather", None, ToolSchema({
        "type": "object",
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
        "additionalProperties": False,
    }))


def call(identifier: str = "call-1", parsed: object = None) -> ToolCall:
    return ToolCall(ToolCallId(identifier), "get_weather", ToolArguments(parsed=parsed))


def test_p4_ac009_identity_not_arguments_equality() -> None:
    args = ToolArguments(parsed={"city": "Paris"})
    one = ToolCall(ToolCallId("id-1"), "get_weather", args)
    two = ToolCall(ToolCallId("id-2"), "get_weather", args)
    duplicate = ToolCall(ToolCallId("id-1"), "get_weather", ToolArguments(parsed={"city": "Lyon"}))
    assert one != two
    assert one == duplicate
    assert len({one, two, duplicate}) == 2


@pytest.mark.parametrize("bad", ["", " ", "\t", "x" * 257, None, 42, True])
def test_p4_ac010_invalid_call_ids_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="ToolCallId"):
        ToolCallId(cast(str, bad))


def test_p4_ac011_unknown_tool_is_explicit_failure() -> None:
    unknown = ToolCall(ToolCallId("id"), "other_tool", ToolArguments(parsed={}))
    with pytest.raises(DomainValidationError, match="unavailable"):
        validate_tool_call(unknown, (tool(),))


def test_p4_ac012_raw_and_parsed_are_not_equivalent() -> None:
    raw_only = ToolArguments(raw='{"city":"Paris"}')
    parsed_null = ToolArguments(raw='{"city":"Paris"}', parsed=None)
    parsed_ok = ToolArguments(raw="opaque", parsed={"city": "Paris"})
    assert raw_only.has_parsed is False and raw_only.parsed is None
    assert parsed_null.has_parsed is True and parsed_null.parsed is None
    assert parsed_ok.has_parsed is True and parsed_ok.parsed == {"city": "Paris"}
    assert raw_only != parsed_null
    raw_call = ToolCall(ToolCallId("raw-only"), "get_weather", raw_only)
    assert validate_tool_call(raw_call, (tool(),)).status is ValidationStatus.UNKNOWN
    assert validate_tool_call(
        ToolCall(ToolCallId("parsed-ok"), "get_weather", parsed_ok), (tool(),)
    ).status is ValidationStatus.VALID


def test_p4_ac013_invalid_arguments_report_not_executed() -> None:
    invalid = ToolCall(ToolCallId("invalid"), "get_weather", ToolArguments(parsed={"city": 12}))
    assessment = validate_tool_call(invalid, (tool(),))
    assert assessment.status is ValidationStatus.INVALID
    assert assessment.code == "type_mismatch"
    with pytest.raises(DomainValidationError, match="evidence"):
        ToolCallValidation(ValidationStatus.VALID, None)


def test_p4_ac014_orphan_result_rejected() -> None:
    known = call("known")
    with pytest.raises(DomainValidationError, match="unknown ToolCallId"):
        attach_tool_result((known,), (), ToolResult(ToolCallId("orphan"), {"ok": True}))


def test_p4_ac015_duplicate_final_result_rejected() -> None:
    known = call("known")
    first = ToolResult(known.call_id, {"ok": True})
    assert attach_tool_result((known,), (), first) == (first,)
    with pytest.raises(DomainValidationError, match="duplicate final"):
        attach_tool_result((known,), (first,), ToolResult(known.call_id, {"ok": True}))


def test_p4_ac016_error_result_and_redaction() -> None:
    failure = ToolResult(ToolCallId("id"), {"secret": "PRIVATE_TOKEN"}, is_error=True)
    assert failure.is_error is True
    assert failure.value == {"secret": "PRIVATE_TOKEN"}
    assert "PRIVATE_TOKEN" not in repr(failure)
    args = ToolArguments(raw="VERY_PRIVATE_TOKEN", parsed={"secret": "PRIVATE_TOKEN"})
    assert "PRIVATE_TOKEN" not in repr(args)
    with pytest.raises(DomainValidationError, match="boolean"):
        ToolResult(ToolCallId("id"), None, is_error=cast(bool, 1))
