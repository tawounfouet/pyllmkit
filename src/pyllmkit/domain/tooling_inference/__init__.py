"""P4 composition isolated from the qualified M3 inference API (ADR-028)."""

from .composition import ToolCallOutput, ToolingInferenceIntent, ToolingInferenceObservation
from .serialization import (
    intent_from_dict,
    intent_to_dict,
    observation_from_dict,
    observation_to_dict,
    tool_call_output_from_dict,
    tool_call_output_to_dict,
)
from .support import ToolingSupportReport, evaluate_tooling_support, validate_tooling_support

__all__ = [
    "ToolCallOutput",
    "ToolingInferenceIntent",
    "ToolingInferenceObservation",
    "ToolingSupportReport",
    "evaluate_tooling_support",
    "intent_from_dict",
    "intent_to_dict",
    "observation_from_dict",
    "observation_to_dict",
    "tool_call_output_from_dict",
    "tool_call_output_to_dict",
    "validate_tooling_support",
]
