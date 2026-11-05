"""P4-AC-025..032: verified P4 composition, codec and M3 compatibility."""

import json
from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    InferenceRequest,
    InferenceResponse,
    InferenceRunId,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
    TextOutput,
    request_from_dict,
    request_to_dict,
    response_from_dict,
    response_to_dict,
)
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
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
    ValidationStatus,
)
from pyllmkit.domain.tooling.serialization import (
    TOOLING_SCHEMA_VERSION,
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
    validate_tooling_support,
)


def request() -> InferenceRequest:
    return InferenceRequest(
        ModelTarget(ModelId("offline-model")),
        (Message(Role.USER, Content((TextContent("Hello"),))),),
    )


def tool(name: str = "get_weather") -> Tool:
    return Tool(
        name, "Descriptive weather tool",
        ToolSchema({
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        }),
    )


def call(uid: str = "call-1") -> ToolCall:
    return ToolCall(ToolCallId(uid), "get_weather", ToolArguments(
        raw='{"city":"Paris"}', parsed={"city": "Paris"}
    ))


def json_cycle(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=True, allow_nan=False))


def test_p4_ac025_compose_m3_without_mutating_it() -> None:
    original = request()
    before = request_to_dict(original)
    for tools in ((), (tool(),), (tool(), tool("search"))):
        choice = ToolChoice.specific("get_weather") if tools else None
        intent = ToolingInferenceIntent(original, tools, choice)
        assert intent.request is original
        assert intent_from_dict(json_cycle(intent_to_dict(intent))) == intent
    assert request_to_dict(original) == before
    with pytest.raises(DomainValidationError, match="declared"):
        ToolingInferenceIntent(original, (tool(),), ToolChoice.specific("missing"))


def test_p4_ac026_known_unsupported_tools_rejected() -> None:
    intent = ToolingInferenceIntent(request(), (tool(),))
    report = evaluate_tooling_support(intent, CapabilitySupport(SupportLevel.UNSUPPORTED))
    assert report.is_compatible is False
    with pytest.raises(DomainValidationError, match="unsupported"):
        validate_tooling_support(intent, CapabilitySupport(SupportLevel.UNSUPPORTED))


def test_p4_ac027_unknown_schema_support_never_native() -> None:
    fmt = SchemaResponseFormat(ToolSchema({"type": "object"}))
    intent = ToolingInferenceIntent(request(), response_format=fmt)
    assessment = evaluate_tooling_support(intent)
    assert assessment.requires_structured_output
    assert assessment.structured_level is None
    assert assessment.is_compatible is None
    assert validate_tooling_support(intent).is_compatible is None
    assert evaluate_tooling_support(
        intent, structured_support=CapabilitySupport(SupportLevel.NATIVE)
    ).is_compatible is True


def test_p4_ac028_tool_call_output_not_fictional_execution() -> None:
    observed = ToolCallOutput((call(),))
    assert not hasattr(observed, "execute")
    assert not hasattr(observed, "result")
    observation = ToolingInferenceObservation(call_output=observed)
    assert observation.results == ()
    assert observation.run_id is None
    assert observation.structured_output is None
    assert tool_call_output_from_dict(json_cycle(tool_call_output_to_dict(observed))) == observed


def test_p4_ac029_inference_v1_refuses_p4_without_drop() -> None:
    wrapped = ToolingInferenceIntent(request(), (tool(),))
    with pytest.raises(DomainValidationError, match="InferenceRequest"):
        request_to_dict(cast(InferenceRequest, wrapped))
    original = request_to_dict(request())
    expanded = {**original, "tools": [tool_to_dict(tool())]}
    with pytest.raises(DomainValidationError, match="unknown"):
        request_from_dict(expanded)
    assert set(original) == {
        "schema_version", "object_type", "target", "messages", "generation_config",
    }


def test_p4_ac030_tooling_json_v1_lossless_roundtrip() -> None:
    t = tool()
    c = call()
    result = ToolResult(c.call_id, {"numbers": [1, 2]}, is_error=True)
    fmt = SchemaResponseFormat(ToolSchema({"type": "object"}), strict=False)
    structured = validate_structured_output(
        StructuredOutput(fmt, raw='{"ok":true}', parsed={"ok": True})
    )
    values = (
        (t, tool_to_dict, tool_from_dict),
        (ToolChoice.specific("get_weather"), tool_choice_to_dict, tool_choice_from_dict),
        (c, tool_call_to_dict, tool_call_from_dict),
        (result, tool_result_to_dict, tool_result_from_dict),
        (fmt, response_format_to_dict, response_format_from_dict),
        (structured, structured_output_to_dict, structured_output_from_dict),
    )
    for value, encoder, decoder in values:
        encoded = encoder(value)
        assert encoded["schema_version"] == TOOLING_SCHEMA_VERSION
        assert encoder(decoder(json_cycle(encoded))) == encoded
        assert tooling_to_dict(tooling_from_dict(json_cycle(encoded))) == encoded
    intent = ToolingInferenceIntent(request(), (t,), ToolChoice.specific(t.name), fmt)
    assert intent_to_dict(intent_from_dict(json_cycle(intent_to_dict(intent)))) == intent_to_dict(intent)
    observation = ToolingInferenceObservation(
        call_output=ToolCallOutput((c,)), structured_output=structured,
        results=(result,), run_id=InferenceRunId("explicit-run"),
    )
    assert observation_to_dict(observation_from_dict(json_cycle(
        observation_to_dict(observation)
    ))) == observation_to_dict(observation)


def test_p4_ac031_unknown_version_and_variant_are_rejected() -> None:
    encoded = tool_to_dict(tool())
    for bad in (
        {**encoded, "schema_version": 2},
        {**encoded, "schema_version": True},
        {**encoded, "object_type": "unrecognized"},
        {**encoded, "injected": 1},
    ):
        with pytest.raises(DomainValidationError):
            tooling_from_dict(bad)


def test_p4_ac032_legacy_inference_json_v1_unchanged() -> None:
    req = request()
    response = InferenceResponse(InferenceRunId("r"), TextOutput("answer"))
    assert request_to_dict(request_from_dict(json_cycle(request_to_dict(req)))) == request_to_dict(req)
    assert response_to_dict(response_from_dict(json_cycle(
        response_to_dict(response)
    ))) == response_to_dict(response)
    assert "tool_calls" not in response_to_dict(response)
    assert "response_format" not in request_to_dict(req)


def test_p4_ac038_reject_malicious_schema_and_unsupported_extensions() -> None:
    encoded = tool_to_dict(tool())
    malformed = {**encoded, "schema": {"$ref": "https://example.test/remote"}}
    with pytest.raises(DomainValidationError, match="unsupported keyword"):
        tool_from_dict(malformed)
    bad = tool_call_to_dict(call())
    args = cast(dict[str, object], bad["arguments"])
    args["parsed_present"] = True
    args["parsed"] = {"value": float("nan")}
    with pytest.raises(DomainValidationError, match="finite"):
        tool_call_from_dict(bad)


def test_p4_ac039_never_leak_raw_in_serialization_errors() -> None:
    secret = "DO_NOT_LEAK_MY_SECRET_TOKEN"
    output = StructuredOutput(JsonResponseFormat(), raw=secret)
    encoded = structured_output_to_dict(output)
    encoded["validation_status"] = "valid"
    with pytest.raises(DomainValidationError) as exc:
        structured_output_from_dict(encoded)
    assert secret not in str(exc.value)
    assert secret not in repr(output)
    assert output.validation.status is ValidationStatus.UNKNOWN
