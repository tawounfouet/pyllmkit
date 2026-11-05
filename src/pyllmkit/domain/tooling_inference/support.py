"""Explicit P4 capability evaluation; M3 GenerationSupportSnapshot untouched."""

from dataclasses import dataclass

from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import JsonResponseFormat, SchemaResponseFormat

from .composition import ToolingInferenceIntent


@dataclass(frozen=True, slots=True)
class ToolingSupportReport:
    """Three-valued compatibility, with UNKNOWN/PARTIAL/EMULATED unconfirmed."""

    requires_tool_calling: bool
    requires_structured_output: bool
    tool_level: SupportLevel | None
    structured_level: SupportLevel | None

    @property
    def is_compatible(self) -> bool | None:
        for needed, level in (
            (self.requires_tool_calling, self.tool_level),
            (self.requires_structured_output, self.structured_level),
        ):
            if needed and level is SupportLevel.UNSUPPORTED:
                return False
        for needed, level in (
            (self.requires_tool_calling, self.tool_level),
            (self.requires_structured_output, self.structured_level),
        ):
            if needed and level is not SupportLevel.NATIVE:
                return None
        return True


def evaluate_tooling_support(
    intent: ToolingInferenceIntent,
    tool_support: CapabilitySupport | None = None,
    structured_support: CapabilitySupport | None = None,
) -> ToolingSupportReport:
    """Evaluate only supplied support declarations; never perform provider I/O."""
    if type(intent) is not ToolingInferenceIntent:
        raise DomainValidationError("tooling support requires a ToolingInferenceIntent")
    if tool_support is not None and type(tool_support) is not CapabilitySupport:
        raise DomainValidationError("tool_support must be CapabilitySupport or None")
    if structured_support is not None and type(structured_support) is not CapabilitySupport:
        raise DomainValidationError("structured_support must be CapabilitySupport or None")
    tools_required = bool(intent.tools)
    output_required = type(intent.response_format) in (JsonResponseFormat, SchemaResponseFormat)
    return ToolingSupportReport(
        requires_tool_calling=tools_required,
        requires_structured_output=output_required,
        tool_level=tool_support.level if tools_required and tool_support is not None else None,
        structured_level=(
            structured_support.level
            if output_required and structured_support is not None else None
        ),
    )


def validate_tooling_support(
    intent: ToolingInferenceIntent,
    tool_support: CapabilitySupport | None = None,
    structured_support: CapabilitySupport | None = None,
) -> ToolingSupportReport:
    """Reject known UNSUPPORTED; preserve UNKNOWN and limited levels verbatim."""
    report = evaluate_tooling_support(intent, tool_support, structured_support)
    if report.is_compatible is False:
        raise DomainValidationError("requested tooling or structured output is unsupported")
    return report
