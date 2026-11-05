"""Explicit declared capability assessment for Structured Output requests."""

from dataclasses import dataclass

from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError

from .formats import JsonResponseFormat, ResponseFormat, SchemaResponseFormat, TextResponseFormat


@dataclass(frozen=True, slots=True)
class ResponseSupportAssessment:
    """Support levels remain distinct; UNKNOWN is never upgraded to NATIVE."""

    requires_structured_output: bool
    level: SupportLevel | None

    @property
    def is_confirmed_native(self) -> bool:
        return self.requires_structured_output and self.level is SupportLevel.NATIVE

    @property
    def is_compatible(self) -> bool | None:
        if not self.requires_structured_output:
            return True
        if self.level is SupportLevel.UNSUPPORTED:
            return False
        if self.level is SupportLevel.NATIVE:
            return True
        return None


def evaluate_response_support(
    response_format: ResponseFormat | None,
    declared_support: CapabilitySupport | None = None,
) -> ResponseSupportAssessment:
    """Evaluate only caller-provided evidence, never query a provider."""
    if response_format is not None and type(response_format) not in (
        TextResponseFormat, JsonResponseFormat, SchemaResponseFormat,
    ):
        raise DomainValidationError("invalid response format")
    if declared_support is not None and type(declared_support) is not CapabilitySupport:
        raise DomainValidationError("declared_support must be CapabilitySupport or None")
    required = type(response_format) in (JsonResponseFormat, SchemaResponseFormat)
    return ResponseSupportAssessment(
        required,
        declared_support.level if required and declared_support is not None else None,
    )


def validate_response_support(
    response_format: ResponseFormat | None,
    declared_support: CapabilitySupport | None = None,
) -> ResponseSupportAssessment:
    """Known UNSUPPORTED is rejected; UNKNOWN/PARTIAL/EMULATED stay explicit."""
    report = evaluate_response_support(response_format, declared_support)
    if report.is_compatible is False:
        raise DomainValidationError("structured output capability is unsupported")
    return report
