"""P4-L4.4 defensive codec branches and declared composition invariants."""

from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    InferenceRequest,
    InferenceRunId,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
)
from pyllmkit.domain.capabilities import CapabilitySupport
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    TextResponseFormat,
    validate_structured_output,
)
from pyllmkit.domain.tooling import (
    Tool,
    ToolArguments,
    ToolCall,
    ToolCallId,
    ToolChoice,
    ToolResult,
    ToolSchema,
)
from pyllmkit.domain.tooling.serialization import (
    response_format_from_dict,
    response_format_to_dict,
    structured_output_from_dict,
    structured_output_to_dict,
    tool_call_from_dict,
    tool_call_to_dict,
    tool_choice_from_dict,
    tool_choice_to_dict,
    tool_from_dict,
    tool_result_from_dict,
    tool_result_to_dict,
    tool_to_dict,
    tooling_from_dict,
    tooling_to_dict,
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


def _request() -> InferenceRequest:
    return InferenceRequest(ModelTarget(ModelId("model")), (
        Message(Role.USER, Content((TextContent("hi"),))),
    ))


def _tool() -> Tool:
    return Tool("known", "description", ToolSchema({"type": "object"}))


def _call() -> ToolCall:
    return ToolCall(ToolCallId("id"), "known", ToolArguments(parsed={"x": 1}))


@pytest.mark.parametrize("bad", [None, 5, [], {"invalid": True}])
def test_tool_decoder_rejects_invalid_envelopes(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        tool_from_dict(cast(dict[str, object], bad))


@pytest.mark.parametrize("change", [
    {"description": False},
    {"schema": None},
    {"schema_version": "1"},
    {"schema_version": 9},
    {"object_type": "tool_call"},
    {"name": []},
])
def test_tool_decoder_rejects_malformed_fields(change: dict[str, object]) -> None:
    payload = {**tool_to_dict(_tool()), **change}
    with pytest.raises(DomainValidationError):
        tool_from_dict(payload)


@pytest.mark.parametrize("payload", [
    {"schema_version": 1, "object_type": "tool_choice", "kind": "none", "name": "known"},
    {"schema_version": 1, "object_type": "tool_choice", "kind": "specific_tool", "name": None},
    {"schema_version": 1, "object_type": "tool_choice", "kind": "auto", "name": False},
])
def test_invalid_tool_choices_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(DomainValidationError):
        tool_choice_from_dict(payload)


@pytest.mark.parametrize("payload", [
    {"raw": None, "parsed_present": False},
    {"raw": None, "parsed_present": False, "parsed": {}, "extra": 1},
    {"raw": 42, "parsed_present": False, "parsed": None},
    {"raw": None, "parsed_present": "false", "parsed": None},
])
def test_bad_raw_parsed_envelopes_are_rejected(payload: dict[str, object]) -> None:
    envelope = {**tool_call_to_dict(_call()), "arguments": payload}
    with pytest.raises(DomainValidationError):
        tool_call_from_dict(envelope)


def test_tool_result_is_immutable_and_rejects_payload_or_ids() -> None:
    result = tool_result_to_dict(ToolResult(ToolCallId("id"), {"x": 1}))
    for payload in [
        {**result, "value": object()},
        {**result, "call_id": []},
        {**result, "is_error": None},
    ]:
        with pytest.raises(DomainValidationError):
            tool_result_from_dict(payload)


def test_output_codec_rejects_invalid_evidence_or_format_kind() -> None:
    output = validate_structured_output(StructuredOutput(
        SchemaResponseFormat(ToolSchema({"type": "object"})),
        raw="hidden", parsed={"name": "value"},
    ))
    blob = structured_output_to_dict(output)
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "validation_status": "validated"})
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "validation_code": 99})
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "parsed_present": 1})
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "response_format": []})
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "raw": object()})
    with pytest.raises(DomainValidationError):
        structured_output_from_dict({**blob, "parsed": object()})


def test_format_variants_and_strict_null_remain_distinct() -> None:
    schema = SchemaResponseFormat(ToolSchema({}), strict=None)
    assert response_format_from_dict(response_format_to_dict(schema)) == schema
    assert response_format_from_dict(response_format_to_dict(
        TextResponseFormat()
    )) == TextResponseFormat()
    invalid = response_format_to_dict(JsonResponseFormat(strict=None))
    for data in [
        {**invalid, "kind": 1},
        {**invalid, "kind": "other"},
        {**invalid, "strict": "false"},
    ]:
        with pytest.raises(DomainValidationError):
            response_format_from_dict(data)
    with pytest.raises(DomainValidationError):
        response_format_to_dict(cast(TextResponseFormat, {}))


@pytest.mark.parametrize("entity,encoder", [
    (None, tool_to_dict),
    (None, tool_choice_to_dict),
    (None, tool_call_to_dict),
    (None, tool_result_to_dict),
    (None, structured_output_to_dict),
])
def test_encoder_type_guards(entity: object, encoder: object) -> None:
    with pytest.raises(DomainValidationError):
        cast(object, encoder)(entity)  # type: ignore[operator]


def test_generic_tooling_dispatch_rejects_unknown_and_wrong_types() -> None:
    with pytest.raises(DomainValidationError):
        tooling_to_dict(cast(Tool, object()))
    for bad in [
        {"schema_version": 1, "object_type": "other"},
        {"schema_version": 1, "object_type": None},
        cast(dict[str, object], {99: "invalid"}),
    ]:
        with pytest.raises(DomainValidationError):
            tooling_from_dict(bad)
    choice = ToolChoice.specific("known")
    assert tooling_from_dict(tooling_to_dict(choice)) == choice


def test_composition_constructor_type_guards() -> None:
    req = _request()
    with pytest.raises(DomainValidationError, match="request"):
        ToolingInferenceIntent(cast(InferenceRequest, None))
    with pytest.raises(DomainValidationError):
        ToolingInferenceIntent(req, cast(tuple[Tool, ...], []))
    with pytest.raises(DomainValidationError, match="response_format"):
        ToolingInferenceIntent(req, response_format=cast(TextResponseFormat, 1))
    with pytest.raises(DomainValidationError, match="calls"):
        ToolCallOutput(cast(tuple[ToolCall, ...], []))
    with pytest.raises(DomainValidationError, match="calls"):
        ToolCallOutput(cast(tuple[ToolCall, ...], (None,)))
    with pytest.raises(DomainValidationError, match="call_output"):
        ToolingInferenceObservation(call_output=cast(ToolCallOutput, "x"))
    with pytest.raises(DomainValidationError, match="structured_output"):
        ToolingInferenceObservation(structured_output=cast(StructuredOutput, 2))
    with pytest.raises(DomainValidationError, match="run_id"):
        ToolingInferenceObservation(call_output=ToolCallOutput((_call(),)), run_id=cast(
            InferenceRunId, "wrong"
        ))
    with pytest.raises(DomainValidationError, match="results"):
        ToolingInferenceObservation(call_output=ToolCallOutput((_call(),)), results=cast(
            tuple[ToolResult, ...], []
        ))


def test_composite_codec_rejects_non_json_and_extra_fields() -> None:
    call_output = tool_call_output_to_dict(ToolCallOutput((_call(),)))
    with pytest.raises(DomainValidationError):
        tool_call_output_from_dict({**call_output, "calls": 4})
    with pytest.raises(DomainValidationError):
        tool_call_output_from_dict({**call_output, "schema_version": True})
    with pytest.raises(DomainValidationError):
        tool_call_output_from_dict({**call_output, "object_type": "different"})
    with pytest.raises(DomainValidationError):
        tool_call_output_from_dict(cast(dict[str, object], {42: 1}))
    with pytest.raises(DomainValidationError):
        tool_call_output_to_dict(cast(ToolCallOutput, None))

    intent = intent_to_dict(ToolingInferenceIntent(_request()))
    with pytest.raises(DomainValidationError):
        intent_from_dict({**intent, "request": "not a dict"})
    with pytest.raises(DomainValidationError):
        intent_from_dict({**intent, "tools": 4})
    with pytest.raises(DomainValidationError):
        intent_from_dict({**intent, "tool_choice": []})
    with pytest.raises(DomainValidationError):
        intent_from_dict({**intent, "response_format": []})
    with pytest.raises(DomainValidationError):
        intent_to_dict(cast(ToolingInferenceIntent, 10))


def test_observation_codec_rejects_invalid_nested_shapes() -> None:
    sample = observation_to_dict(ToolingInferenceObservation(
        call_output=ToolCallOutput((_call(),)),
    ))
    bad = [
        {**sample, "run_id": {}},
        {**sample, "call_output": []},
        {**sample, "structured_output": []},
        {**sample, "results": [None]},
        {**sample, "object_type": "other"},
        {**sample, "schema_version": 99},
    ]
    for payload in bad:
        with pytest.raises(DomainValidationError):
            observation_from_dict(payload)
    with pytest.raises(DomainValidationError):
        observation_to_dict(cast(ToolingInferenceObservation, "x"))


def test_support_report_does_not_invent_capabilities() -> None:
    req = ToolingInferenceIntent(_request())
    assert evaluate_tooling_support(req).is_compatible is True
    with pytest.raises(DomainValidationError, match="intent"):
        evaluate_tooling_support(cast(ToolingInferenceIntent, None))
    with pytest.raises(DomainValidationError, match="structured_support"):
        evaluate_tooling_support(req, structured_support=cast(CapabilitySupport, "native"))
