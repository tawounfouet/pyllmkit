"""Local, immutable ToolCall validation and ToolResult attachment (ADR-023/025)."""

from dataclasses import dataclass
from enum import StrEnum

from pyllmkit.domain.errors import DomainValidationError

from .calls import ToolCall, ToolResult
from .definitions import Tool, validate_tool_set
from .identifiers import ToolCallId
from .value_validation import check_p4_json_value

_VALIDATION_TOKEN = object()


class ValidationStatus(StrEnum):
    """No implicit promotion from UNKNOWN to VALID."""

    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True, init=False)
class ToolCallValidation:
    """Validation evidence, only constructible through the domain validator API."""

    status: ValidationStatus
    code: str | None

    def __init__(
        self,
        status: ValidationStatus,
        code: str | None,
        *,
        _proof: object = None,
    ) -> None:
        if _proof is not _VALIDATION_TOKEN:
            raise DomainValidationError("ToolCallValidation requires validation evidence")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "code", code)


def _result(status: ValidationStatus, code: str | None = None) -> ToolCallValidation:
    return ToolCallValidation(status, code, _proof=_VALIDATION_TOKEN)


def validate_tool_call(call: ToolCall, tools: tuple[Tool, ...]) -> ToolCallValidation:
    """Assess parsed arguments against the declared schema, without running tools.

    Raw argument text is NOT parsed and never treated as evidence of validity.
    Unknown tools are rejected rather than silently ignored.
    """
    if type(call) is not ToolCall:
        raise DomainValidationError("validate_tool_call expects a ToolCall")
    available = validate_tool_set(tools)
    names = {tool.name: tool for tool in available}
    if call.tool_name not in names:
        raise DomainValidationError("ToolCall references an unavailable Tool")
    if not call.arguments.has_parsed:
        return _result(ValidationStatus.UNKNOWN, "parsed_absent")
    error = check_p4_json_value(call.arguments.parsed, names[call.tool_name].schema)
    if error is not None:
        return _result(ValidationStatus.INVALID, error)
    return _result(ValidationStatus.VALID)


def attach_tool_result(
    calls: tuple[ToolCall, ...],
    results: tuple[ToolResult, ...],
    result: ToolResult,
) -> tuple[ToolResult, ...]:
    """Return a new result collection iff every final result is locally correlated.

    No tool is executed, and at most one final ToolResult per ToolCallId exists.
    """
    if type(calls) is not tuple or any(type(c) is not ToolCall for c in calls):
        raise DomainValidationError("calls must be tuple[ToolCall, ...]")
    if type(results) is not tuple or any(type(r) is not ToolResult for r in results):
        raise DomainValidationError("results must be tuple[ToolResult, ...]")
    if type(result) is not ToolResult:
        raise DomainValidationError("result must be ToolResult")
    ids: set[ToolCallId] = set()
    for call in calls:
        if call.call_id in ids:
            raise DomainValidationError("duplicate ToolCallId in correlation context")
        ids.add(call.call_id)
    result_ids: set[ToolCallId] = set()
    for existing in results:
        if existing.call_id not in ids:
            raise DomainValidationError("existing ToolResult is orphaned")
        if existing.call_id in result_ids:
            raise DomainValidationError("duplicate final ToolResult")
        result_ids.add(existing.call_id)
    if result.call_id not in ids:
        raise DomainValidationError("ToolResult references an unknown ToolCallId")
    if result.call_id in result_ids:
        raise DomainValidationError("duplicate final ToolResult")
    return (*results, result)
