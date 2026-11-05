"""P4 L4.4 negative codec cases and identity/validation round-trips."""

from copy import deepcopy
from typing import cast

import pytest

from pyllmkit.domain import Content, InferenceRequest, Message, ModelId, ModelTarget, Role, TextContent
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    StructuredOutput,
    TextResponseFormat,
    validate_structured_output,
)
from pyllmkit.domain.tooling import (
    Tool,
    ToolArguments,
    ToolCall,
    ToolCallId,
    ToolResult,
    ToolSchema,
    ValidationStatus,
)
from pyllmkit.domain.tooling.serialization import (
    response_format_from_dict,
    response_format_to_dict,
    structured_output_from_dict,
    structured_output_to_dict,
    tool_call_from_dict,
    tool_call_to_dict,
    tool_choice_from_dict,
    tool_from_dict,
    tool_result_from_dict,
    tool_result_to_dict,
)
from pyllmkit.domain.tooling_inference import (
    ToolCallOutput,
    ToolingInferenceIntent,
    ToolingInferenceObservation,
    evaluate_tooling_support,
    intent_from_dict,
    intent_to_dict,
    observation_from_dict,
    observation_to_dict,
    tool_call_output_from_dict,
    tool_call_output_to_dict,
)


def sample_request() -> InferenceRequest:
    return InferenceRequest(ModelTarget(ModelId("m")), (
        Message(Role.USER, Content((TextContent("x"),))),
    ))


def sample_call() -> ToolCall:
    return ToolCall(ToolCallId("c"), "get_weather", ToolArguments(raw="sensitive"))


def test_raw_only_and_explicit_null_roundtrip_exactly() -> None:
    initial = sample_call()
    encoded = tool_call_to_dict(initial)
    decoded = tool_call_from_dict(deepcopy(encoded))
    assert decoded.arguments.raw == "sensitive"
    assert decoded.arguments.has_parsed is False
    assert tool_call_to_dict(decoded) == encoded
    explicit_null = ToolCall(
        ToolCallId("c"), "get_weather", ToolArguments(raw="sensitive", parsed=None)
    )
    encoded_null = tool_call_to_dict(explicit_null)
    assert encoded_null != encoded
    assert tool_call_from_dict(encoded_null).arguments.has_parsed


def test_structured_validation_proof_roundtrips_without_forgery() -> None:
    fmt = JsonResponseFormat(strict=False)
    raw_only = StructuredOutput(fmt, raw='{"x":1}')
    unknown = validate_structured_output(raw_only)
    for obj in (raw_only, unknown, validate_structured_output(
        StructuredOutput(fmt, raw="opaque", parsed=None)
    )):
        encoded = structured_output_to_dict(obj)
        restored = structured_output_from_dict(encoded)
        assert structured_output_to_dict(restored) == encoded
    forged = structured_output_to_dict(raw_only)
    forged["validation_status"] = "valid"
    forged["validation_code"] = None
    with pytest.raises(DomainValidationError, match="evidence mismatch"):
        structured_output_from_dict(forged)


def test_exact_fields_and_bool_version_rejections() -> None:
    tool = Tool("x", None, ToolSchema({}))
    value = {"schema_version": 1, "object_type": "tool_definition",
             "name": tool.name, "description": None, "schema": {}}
    with pytest.raises(DomainValidationError, match="unknown fields"):
        tool_from_dict({**value, "unexpected": None})
    with pytest.raises(DomainValidationError):
        tool_from_dict({**value, "schema_version": True})
    with pytest.raises(DomainValidationError):
        tool_from_dict({**value, "name": 9})
    with pytest.raises(DomainValidationError):
        tool_choice_from_dict({"schema_version": 1, "object_type": "tool_choice",
                               "kind": "wrong", "name": None})


def test_nested_shape_errors_and_conflicting_absence() -> None:
    call = tool_call_to_dict(sample_call())
    args = cast(dict[str, object], call["arguments"])
    args["parsed"] = {"arbitrary": "value"}
    with pytest.raises(DomainValidationError, match="absent parsed"):
        tool_call_from_dict(call)
    args["parsed_present"] = 1
    with pytest.raises(DomainValidationError, match="exact boolean"):
        tool_call_from_dict(call)
    with pytest.raises(DomainValidationError):
        tool_call_from_dict({**call, "call_id": None})
    result = tool_result_to_dict(ToolResult(ToolCallId("id"), {"ok": True}))
    with pytest.raises(DomainValidationError, match="boolean"):
        tool_result_from_dict({**result, "is_error": 0})


def test_formats_reject_invalid_schema_and_ambiguous_strict() -> None:
    text_fmt = response_format_to_dict(TextResponseFormat())
    with pytest.raises(DomainValidationError, match="does not accept strict"):
        response_format_from_dict({**text_fmt, "strict": False})
    json_fmt = response_format_to_dict(JsonResponseFormat())
    with pytest.raises(DomainValidationError, match="does not accept schema"):
        response_format_from_dict({**json_fmt, "schema": {}})
    with pytest.raises(DomainValidationError, match="bool or null"):
        response_format_from_dict({**json_fmt, "strict": 0})


def test_correlation_and_composition_are_never_silently_weakened() -> None:
    call = sample_call()
    with pytest.raises(DomainValidationError, match="duplicate"):
        ToolCallOutput((call, call))
    with pytest.raises(DomainValidationError, match="duplicate"):
        ToolingInferenceObservation(ToolCallOutput((call,)), results=(
            ToolResult(call.call_id, {}), ToolResult(call.call_id, {})
        ))
    with pytest.raises(DomainValidationError, match="unknown ToolCallId"):
        ToolingInferenceObservation(ToolCallOutput((call,)), results=(
            ToolResult(ToolCallId("orphan"), {}),
        ))
    with pytest.raises(DomainValidationError, match="requires"):
        ToolingInferenceObservation()
    with pytest.raises(DomainValidationError, match="declared"):
        ToolingInferenceIntent(
            sample_request(), (Tool("x", None, ToolSchema({})),),
            tool_choice_from_dict({
                "schema_version": 1, "object_type": "tool_choice",
                "kind": "specific_tool", "name": "missing",
            }),
        )


def test_nested_envelopes_are_strict_and_preserve_identity() -> None:
    request = ToolingInferenceIntent(sample_request())
    encoded = intent_to_dict(request)
    assert intent_from_dict(encoded) == request
    with pytest.raises(DomainValidationError, match="missing or unknown"):
        intent_from_dict({**encoded, "tools_v2": []})
    calls = ToolCallOutput((sample_call(),))
    call_data = tool_call_output_to_dict(calls)
    with pytest.raises(DomainValidationError, match="missing or unknown"):
        tool_call_output_from_dict({**call_data, "schema_version2": 1})
    observation = ToolingInferenceObservation(calls, run_id=None)
    data = observation_to_dict(observation)
    assert observation_to_dict(observation_from_dict(data)) == data
    with pytest.raises(DomainValidationError, match="array"):
        observation_from_dict({**data, "results": {}})


def test_partial_and_emulated_not_native() -> None:
    intent = ToolingInferenceIntent(
        sample_request(), tools=(Tool("x", None, ToolSchema({})),),
        response_format=JsonResponseFormat(),
    )
    assert evaluate_tooling_support(
        intent,
        CapabilitySupport(SupportLevel.EMULATED),
        CapabilitySupport(SupportLevel.NATIVE),
    ).is_compatible is None
    assert evaluate_tooling_support(
        intent,
        CapabilitySupport(SupportLevel.PARTIAL, notes="limited"),
        CapabilitySupport(SupportLevel.NATIVE),
    ).is_compatible is None
    assert evaluate_tooling_support(
        intent,
        CapabilitySupport(SupportLevel.UNSUPPORTED),
        CapabilitySupport(SupportLevel.NATIVE),
    ).is_compatible is False
    assert evaluate_tooling_support(
        intent,
        CapabilitySupport(SupportLevel.NATIVE),
        CapabilitySupport(SupportLevel.NATIVE),
    ).is_compatible is True
    with pytest.raises(DomainValidationError, match="tool_support"):
        evaluate_tooling_support(intent, cast(CapabilitySupport, "native"))


def test_schema_validation_state_not_invented_on_decode() -> None:
    output = StructuredOutput(JsonResponseFormat(), raw="opaque")
    data = structured_output_to_dict(output)
    data["validation_code"] = "parsed_absent"
    assert output.validation.status is ValidationStatus.UNKNOWN
    with pytest.raises(DomainValidationError, match="evidence mismatch"):
        structured_output_from_dict(data)
