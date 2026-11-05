"""P4-AC-035: full provider-free Tooling and Structured Output walkthrough.

No LLM is queried, no tool is executed, no provider credentials are required.
All observations, including the result, are supplied by this offline example.
"""

import json

from pyllmkit.domain import (
    Content,
    InferenceRequest,
    InferenceRunId,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
    request_to_dict,
)
from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.structured_output import (
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
    attach_tool_result,
    validate_tool_call,
)
from pyllmkit.domain.tooling_inference import (
    ToolCallOutput,
    ToolingInferenceIntent,
    ToolingInferenceObservation,
    intent_from_dict,
    intent_to_dict,
    observation_from_dict,
    observation_to_dict,
    validate_tooling_support,
)


def main() -> None:
    request = InferenceRequest(
        ModelTarget(ModelId("offline-demo-model")),
        (Message(Role.USER, Content((TextContent("Weather in Paris?"),))),),
    )
    tool = Tool(
        "get_weather",
        "Describe weather for a city without executing it",
        ToolSchema({
            "type": "object",
            "properties": {"city": {"type": "string", "minLength": 1}},
            "required": ["city"],
            "additionalProperties": False,
        }),
    )
    output_format = SchemaResponseFormat(
        ToolSchema({
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        }),
        strict=True,
    )
    intent = ToolingInferenceIntent(
        request, (tool,), ToolChoice.specific("get_weather"), output_format,
    )
    support = validate_tooling_support(
        intent,
        tool_support=CapabilitySupport(SupportLevel.NATIVE),
        structured_support=CapabilitySupport(SupportLevel.NATIVE),
    )
    assert support.is_compatible is True

    call = ToolCall(
        ToolCallId("manual-call-001"),
        tool.name,
        ToolArguments(raw='{"city":"Paris"}', parsed={"city": "Paris"}),
    )
    assert validate_tool_call(call, intent.tools).status is ValidationStatus.VALID

    # This JSON is an illustration supplied by the caller, not a real tool execution.
    result = ToolResult(call.call_id, {"temperature_c": 18, "condition": "illustrative"})
    correlated = attach_tool_result((call,), (), result)
    output = validate_structured_output(
        StructuredOutput(
            output_format,
            raw='{"summary":"Illustrative response"}',
            parsed={"summary": "Illustrative response"},
        ),
    )
    assert output.validation.status is ValidationStatus.VALID

    observation = ToolingInferenceObservation(
        call_output=ToolCallOutput((call,)),
        structured_output=output,
        results=correlated,
        run_id=InferenceRunId("manual-run-001"),
    )
    wire_intent = intent_to_dict(intent)
    wire_observation = observation_to_dict(observation)

    assert intent_to_dict(
        intent_from_dict(json.loads(json.dumps(wire_intent)))
    ) == wire_intent
    assert observation_to_dict(
        observation_from_dict(json.loads(json.dumps(wire_observation)))
    ) == wire_observation

    # Qualified M3 Inference JSON v1 does not silently acquire P4 extension fields.
    assert "tools" not in request_to_dict(request)
    assert "tool_choice" not in request_to_dict(request)
    print("P4 tooling walkthrough: validation and round-trips passed (offline, no execution).")


if __name__ == "__main__":
    main()
