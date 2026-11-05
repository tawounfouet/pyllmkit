"""P4 L4.4 - Independent Tooling JSON v1 and unchanged Inference JSON v1."""

import json

from pyllmkit.domain import (
    Content, InferenceRequest, Message, ModelId, ModelTarget, Role, TextContent,
    request_to_dict,
)
from pyllmkit.domain.structured_output import (
    SchemaResponseFormat, StructuredOutput, validate_structured_output,
)
from pyllmkit.domain.tooling import (
    Tool, ToolArguments, ToolCall, ToolCallId, ToolChoice, ToolResult, ToolSchema,
)
from pyllmkit.domain.tooling_inference import (
    ToolCallOutput,
    ToolingInferenceIntent,
    ToolingInferenceObservation,
    intent_from_dict,
    intent_to_dict,
    observation_from_dict,
    observation_to_dict,
)


def main() -> None:
    request = InferenceRequest(ModelTarget(ModelId("offline-model")), (
        Message(Role.USER, Content((TextContent("Weather in Paris?"),))),
    ))
    schema = ToolSchema({
        "type": "object", "properties": {"city": {"type": "string"}},
        "required": ["city"], "additionalProperties": False,
    })
    tool = Tool("get_weather", "Describe weather", schema)
    fmt = SchemaResponseFormat(schema, strict=True)
    intent = ToolingInferenceIntent(request, (tool,), ToolChoice.specific(tool.name), fmt)
    encoded_intent = intent_to_dict(intent)
    decoded_intent = intent_from_dict(json.loads(json.dumps(encoded_intent)))
    assert intent_to_dict(decoded_intent) == encoded_intent

    call = ToolCall(
        ToolCallId("call-001"), tool.name,
        ToolArguments(raw='{"city":"Paris"}', parsed={"city": "Paris"}),
    )
    structured = validate_structured_output(
        StructuredOutput(fmt, parsed={"city": "Paris"}, raw='{"city":"Paris"}')
    )
    observation = ToolingInferenceObservation(
        call_output=ToolCallOutput((call,)), structured_output=structured,
        results=(ToolResult(call.call_id, {"example": True}),),
    )
    encoded_observation = observation_to_dict(observation)
    assert observation_to_dict(observation_from_dict(
        json.loads(json.dumps(encoded_observation))
    )) == encoded_observation
    assert "tools" not in request_to_dict(request)
    print("P4 L4.4: strict Tooling JSON v1 roundtrip, M3 unchanged, no tool execution.")


if __name__ == "__main__":
    main()
