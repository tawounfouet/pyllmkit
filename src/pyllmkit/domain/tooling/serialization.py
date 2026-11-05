"""Strict, independent Tooling JSON-compatible v1 codec (ADR-029).

Transforms immutable P4 domain objects to/from plain JSON-compatible mappings.
It does not parse JSON text, run tools, read files, call providers or silently
convert P4 values into the existing Inference JSON v1 codec.
"""

from collections.abc import Mapping
from typing import TypeAlias, cast

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    ResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    TextResponseFormat,
    validate_structured_output,
)
from pyllmkit.domain.tooling.arguments import ToolArguments
from pyllmkit.domain.tooling.calls import ToolCall, ToolResult
from pyllmkit.domain.tooling.choice import ToolChoice, ToolChoiceKind
from pyllmkit.domain.tooling.definitions import Tool
from pyllmkit.domain.tooling.identifiers import ToolCallId
from pyllmkit.domain.tooling.json_values import freeze_json, thaw_json
from pyllmkit.domain.tooling.schema import ToolSchema
from pyllmkit.domain.tooling.validation import ValidationStatus

TOOLING_SCHEMA_VERSION = 1

_TOOL_FIELDS = frozenset({"schema_version", "object_type", "name", "description", "schema"})
_CHOICE_FIELDS = frozenset({"schema_version", "object_type", "kind", "name"})
_ARGUMENT_FIELDS = frozenset({"raw", "parsed_present", "parsed"})
_CALL_FIELDS = frozenset({"schema_version", "object_type", "call_id", "tool_name", "arguments"})
_RESULT_FIELDS = frozenset({"schema_version", "object_type", "call_id", "is_error", "value"})
_FORMAT_FIELDS = frozenset({"schema_version", "object_type", "kind", "strict", "schema"})
_STRUCTURED_FIELDS = frozenset({
    "schema_version", "object_type", "response_format", "raw",
    "parsed_present", "parsed", "validation_status", "validation_code",
})


def _object(payload: object, label: str) -> dict[str, object]:
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        raise DomainValidationError(f"{label} must be an object with string keys")
    return cast(dict[str, object], payload)


def _fields(payload: object, fields: frozenset[str], label: str) -> dict[str, object]:
    result = _object(payload, label)
    if set(result) != fields:
        raise DomainValidationError(f"{label} has missing or unknown fields")
    return result


def _envelope(payload: object, fields: frozenset[str], kind: str) -> dict[str, object]:
    result = _fields(payload, fields, kind)
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        raise DomainValidationError("unsupported Tooling JSON schema_version")
    if type(result["object_type"]) is not str or result["object_type"] != kind:
        raise DomainValidationError("unsupported Tooling JSON object_type")
    return result


def _string(value: object, name: str) -> str:
    if type(value) is not str:
        raise DomainValidationError(f"{name} must be a string")
    return value


def _optional_string(value: object, name: str) -> str | None:
    return None if value is None else _string(value, name)


def _nullable_bool(value: object, label: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise DomainValidationError(f"{label} must be bool or null")
    return cast(bool | None, value)


def _frozen_copy(value: object) -> object:
    return thaw_json(freeze_json(value))


def _raw_parsed_to_dict(raw: str | None, present: bool, parsed: object) -> dict[str, object]:
    return {
        "raw": raw,
        "parsed_present": present,
        "parsed": _frozen_copy(parsed) if present else None,
    }


def _raw_parsed_from_dict(payload: object) -> tuple[str | None, bool, object]:
    result = _fields(payload, _ARGUMENT_FIELDS, "raw/parsed")
    raw = _optional_string(result["raw"], "raw")
    present = result["parsed_present"]
    if type(present) is not bool:
        raise DomainValidationError("parsed_present must be an exact boolean")
    if not present and result["parsed"] is not None:
        raise DomainValidationError("absent parsed value must use null")
    parsed = _frozen_copy(result["parsed"]) if present else None
    return raw, present, parsed


def tool_to_dict(tool: Tool) -> dict[str, object]:
    if type(tool) is not Tool:
        raise DomainValidationError("tool_to_dict expects Tool")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tool_definition",
        "name": tool.name,
        "description": tool.description,
        "schema": tool.schema.value,
    }


def tool_from_dict(payload: Mapping[str, object]) -> Tool:
    data = _envelope(payload, _TOOL_FIELDS, "tool_definition")
    description = _optional_string(data["description"], "Tool.description")
    schema = _object(data["schema"], "Tool.schema")
    return Tool(_string(data["name"], "Tool.name"), description, ToolSchema(schema))


def tool_choice_to_dict(choice: ToolChoice) -> dict[str, object]:
    if type(choice) is not ToolChoice:
        raise DomainValidationError("tool_choice_to_dict expects ToolChoice")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tool_choice",
        "kind": choice.kind.value,
        "name": choice.name,
    }


def tool_choice_from_dict(payload: Mapping[str, object]) -> ToolChoice:
    data = _envelope(payload, _CHOICE_FIELDS, "tool_choice")
    kind = _string(data["kind"], "ToolChoice.kind")
    if kind not in {item.value for item in ToolChoiceKind}:
        raise DomainValidationError("unsupported ToolChoice kind")
    return ToolChoice(ToolChoiceKind(kind), _optional_string(data["name"], "ToolChoice.name"))


def tool_call_to_dict(call: ToolCall) -> dict[str, object]:
    if type(call) is not ToolCall:
        raise DomainValidationError("tool_call_to_dict expects ToolCall")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tool_call",
        "call_id": call.call_id.value,
        "tool_name": call.tool_name,
        "arguments": _raw_parsed_to_dict(
            call.arguments.raw, call.arguments.has_parsed, call.arguments.parsed
        ),
    }


def tool_call_from_dict(payload: Mapping[str, object]) -> ToolCall:
    data = _envelope(payload, _CALL_FIELDS, "tool_call")
    raw, present, parsed = _raw_parsed_from_dict(data["arguments"])
    args = ToolArguments(raw=raw, parsed=parsed) if present else ToolArguments(raw=raw)
    return ToolCall(
        ToolCallId(_string(data["call_id"], "ToolCallId")),
        _string(data["tool_name"], "tool_name"),
        args,
    )


def tool_result_to_dict(result: ToolResult) -> dict[str, object]:
    if type(result) is not ToolResult:
        raise DomainValidationError("tool_result_to_dict expects ToolResult")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tool_result",
        "call_id": result.call_id.value,
        "is_error": result.is_error,
        "value": _frozen_copy(result.value),
    }


def tool_result_from_dict(payload: Mapping[str, object]) -> ToolResult:
    data = _envelope(payload, _RESULT_FIELDS, "tool_result")
    is_error = data["is_error"]
    if type(is_error) is not bool:
        raise DomainValidationError("ToolResult.is_error must be a boolean")
    return ToolResult(
        ToolCallId(_string(data["call_id"], "ToolCallId")),
        _frozen_copy(data["value"]),
        is_error=is_error,
    )


def response_format_to_dict(fmt: ResponseFormat) -> dict[str, object]:
    if type(fmt) not in (TextResponseFormat, JsonResponseFormat, SchemaResponseFormat):
        raise DomainValidationError("unsupported ResponseFormat type")
    strict: bool | None = None
    schema: object = None
    if isinstance(fmt, (JsonResponseFormat, SchemaResponseFormat)):
        strict = fmt.strict
    if isinstance(fmt, SchemaResponseFormat):
        schema = fmt.schema.value
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "response_format",
        "kind": fmt.kind,
        "strict": strict,
        "schema": schema,
    }


def response_format_from_dict(payload: Mapping[str, object]) -> ResponseFormat:
    data = _envelope(payload, _FORMAT_FIELDS, "response_format")
    kind = _string(data["kind"], "ResponseFormat.kind")
    strict = _nullable_bool(data["strict"], "strict")
    raw_schema = data["schema"]
    if kind == "text":
        if strict is not None or raw_schema is not None:
            raise DomainValidationError("text format does not accept strict or schema")
        return TextResponseFormat()
    if kind == "json":
        if raw_schema is not None:
            raise DomainValidationError("json format does not accept schema")
        return JsonResponseFormat(strict=strict)
    if kind == "json_schema":
        return SchemaResponseFormat(ToolSchema(_object(raw_schema, "response schema")), strict)
    raise DomainValidationError("unsupported ResponseFormat kind")


def structured_output_to_dict(output: StructuredOutput) -> dict[str, object]:
    if type(output) is not StructuredOutput:
        raise DomainValidationError("structured_output_to_dict expects StructuredOutput")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "structured_output",
        "response_format": response_format_to_dict(output.response_format),
        **_raw_parsed_to_dict(output.raw, output.has_parsed, output.parsed),
        "validation_status": output.validation.status.value,
        "validation_code": output.validation.code,
    }


def structured_output_from_dict(payload: Mapping[str, object]) -> StructuredOutput:
    data = _envelope(payload, _STRUCTURED_FIELDS, "structured_output")
    fmt = response_format_from_dict(_object(data["response_format"], "response_format"))
    raw, present, parsed = _raw_parsed_from_dict(
        {key: data[key] for key in _ARGUMENT_FIELDS}
    )
    output = StructuredOutput(fmt, raw=raw, parsed=parsed) if present else StructuredOutput(
        fmt, raw=raw
    )
    status = _string(data["validation_status"], "validation_status")
    if status not in {item.value for item in ValidationStatus}:
        raise DomainValidationError("unsupported StructuredOutput validation_status")
    code = _optional_string(data["validation_code"], "validation_code")
    if status == ValidationStatus.UNKNOWN.value and code == "not_validated":
        return output
    checked = validate_structured_output(output)
    if checked.validation.status.value != status or checked.validation.code != code:
        raise DomainValidationError("StructuredOutput validation evidence mismatch")
    return checked


ToolingValue: TypeAlias = (
    Tool | ToolChoice | ToolCall | ToolResult | ResponseFormat | StructuredOutput
)


def tooling_to_dict(value: ToolingValue) -> dict[str, object]:
    """Dispatch only known P4 value types, never implicitly downgrade to M3."""
    if type(value) is Tool:
        return tool_to_dict(value)
    if type(value) is ToolChoice:
        return tool_choice_to_dict(value)
    if type(value) is ToolCall:
        return tool_call_to_dict(value)
    if type(value) is ToolResult:
        return tool_result_to_dict(value)
    if type(value) in (TextResponseFormat, JsonResponseFormat, SchemaResponseFormat):
        return response_format_to_dict(value)
    if type(value) is StructuredOutput:
        return structured_output_to_dict(value)
    raise DomainValidationError("unsupported Tooling JSON value")


def tooling_from_dict(payload: Mapping[str, object]) -> ToolingValue:
    """Dispatch using exact object_type, reject unknown kinds and v1 extensions."""
    data = _object(payload, "Tooling JSON value")
    kind = _string(data.get("object_type"), "object_type")
    if kind == "tool_definition":
        return tool_from_dict(data)
    if kind == "tool_choice":
        return tool_choice_from_dict(data)
    if kind == "tool_call":
        return tool_call_from_dict(data)
    if kind == "tool_result":
        return tool_result_from_dict(data)
    if kind == "response_format":
        return response_format_from_dict(data)
    if kind == "structured_output":
        return structured_output_from_dict(data)
    raise DomainValidationError("unsupported Tooling JSON object_type")
