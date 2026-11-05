"""Structured output domain, P4 L4.3, ADR-024/025/026/027."""

from .formats import (
    JsonResponseFormat,
    ResponseFormat,
    SchemaResponseFormat,
    TextResponseFormat,
)
from .output import StructuredOutput, StructuredValidationResult, validate_structured_output
from .support import ResponseSupportAssessment, evaluate_response_support, validate_response_support

__all__ = [
    "JsonResponseFormat",
    "ResponseFormat",
    "ResponseSupportAssessment",
    "SchemaResponseFormat",
    "StructuredOutput",
    "StructuredValidationResult",
    "TextResponseFormat",
    "evaluate_response_support",
    "validate_response_support",
    "validate_structured_output",
]
