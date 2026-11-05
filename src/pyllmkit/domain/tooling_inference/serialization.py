"""Strict composition codec: nests existing M3 Inference JSON v1 without mutation.

Only P4 wrappers are new. InferenceRequest, InferenceResponse and M3 codecs
remain unchanged. No JSON text parsing, I/O, provider or tool execution.
"""

from collections.abc import Mapping
from typing import cast

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import InferenceRunId, request_from_dict, request_to_dict
from pyllmkit.domain.structured_output import StructuredOutput
from pyllmkit.domain.tooling import ToolCall, ToolResult
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
)

from .composition import ToolCallOutput, ToolingInferenceIntent, ToolingInferenceObservation

_CALL_OUTPUT_FIELDS = frozenset({"schema_version", "object_type", "calls"})
_INTENT_FIELDS = frozenset({
    "schema_version", "object_type", "request", "tools", "tool_choice", "response_format",
})
_OBSERVATION_FIELDS = frozenset({
    "schema_version", "object_type", "run_id", "call_output", "structured_output", "results",
})


def _object(payload: object, label: str) -> dict[str, object]:
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        raise DomainValidationError(f"{label} must be a JSON object with string keys")
    return cast(dict[str, object], payload)


def _envelope(payload: object, fields: frozenset[str], kind: str) -> dict[str, object]:
    obj = _object(payload, kind)
    if set(obj) != fields:
        raise DomainValidationError(f"{kind} has missing or unknown fields")
    if type(obj["schema_version"]) is not int or obj["schema_version"] != TOOLING_SCHEMA_VERSION:
        raise DomainValidationError("unsupported Tooling schema_version")
    if type(obj["object_type"]) is not str or obj["object_type"] != kind:
        raise DomainValidationError("unsupported Tooling object_type")
    return obj


def _list(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise DomainValidationError(f"{label} must be an array")
    return cast(list[object], value)


def tool_call_output_to_dict(output: ToolCallOutput) -> dict[str, object]:
    if type(output) is not ToolCallOutput:
        raise DomainValidationError("expected ToolCallOutput")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tool_call_output",
        "calls": [tool_call_to_dict(call) for call in output.calls],
    }


def tool_call_output_from_dict(payload: Mapping[str, object]) -> ToolCallOutput:
    data = _envelope(payload, _CALL_OUTPUT_FIELDS, "tool_call_output")
    return ToolCallOutput(
        tuple(tool_call_from_dict(_object(item, "ToolCall")) for item in _list(data["calls"], "calls"))
    )


def intent_to_dict(intent: ToolingInferenceIntent) -> dict[str, object]:
    if type(intent) is not ToolingInferenceIntent:
        raise DomainValidationError("intent_to_dict expects ToolingInferenceIntent")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tooling_inference_intent",
        "request": request_to_dict(intent.request),
        "tools": [tool_to_dict(tool) for tool in intent.tools],
        "tool_choice": (
            tool_choice_to_dict(intent.tool_choice) if intent.tool_choice is not None else None
        ),
        "response_format": (
            response_format_to_dict(intent.response_format)
            if intent.response_format is not None else None
        ),
    }


def intent_from_dict(payload: Mapping[str, object]) -> ToolingInferenceIntent:
    data = _envelope(payload, _INTENT_FIELDS, "tooling_inference_intent")
    raw_choice = data["tool_choice"]
    raw_format = data["response_format"]
    return ToolingInferenceIntent(
        request=request_from_dict(_object(data["request"], "Inference request")),
        tools=tuple(
            tool_from_dict(_object(item, "Tool"))
            for item in _list(data["tools"], "tools")
        ),
        tool_choice=(
            tool_choice_from_dict(_object(raw_choice, "ToolChoice"))
            if raw_choice is not None else None
        ),
        response_format=(
            response_format_from_dict(_object(raw_format, "ResponseFormat"))
            if raw_format is not None else None
        ),
    )


def observation_to_dict(observation: ToolingInferenceObservation) -> dict[str, object]:
    if type(observation) is not ToolingInferenceObservation:
        raise DomainValidationError("observation_to_dict expects ToolingInferenceObservation")
    return {
        "schema_version": TOOLING_SCHEMA_VERSION,
        "object_type": "tooling_inference_observation",
        "run_id": observation.run_id.value if observation.run_id is not None else None,
        "call_output": (
            tool_call_output_to_dict(observation.call_output)
            if observation.call_output is not None else None
        ),
        "structured_output": (
            structured_output_to_dict(observation.structured_output)
            if observation.structured_output is not None else None
        ),
        "results": [tool_result_to_dict(result) for result in observation.results],
    }


def observation_from_dict(payload: Mapping[str, object]) -> ToolingInferenceObservation:
    data = _envelope(payload, _OBSERVATION_FIELDS, "tooling_inference_observation")
    raw_id = data["run_id"]
    if raw_id is not None and type(raw_id) is not str:
        raise DomainValidationError("run_id must be a string or null")
    raw_calls = data["call_output"]
    raw_structured = data["structured_output"]
    return ToolingInferenceObservation(
        call_output=(
            tool_call_output_from_dict(_object(raw_calls, "call_output"))
            if raw_calls is not None else None
        ),
        structured_output=(
            structured_output_from_dict(_object(raw_structured, "structured_output"))
            if raw_structured is not None else None
        ),
        results=tuple(
            tool_result_from_dict(_object(item, "ToolResult"))
            for item in _list(data["results"], "results")
        ),
        run_id=InferenceRunId(raw_id) if raw_id is not None else None,
    )
