"""P4 L4.1 typed tool-selection policies, with no provider routing."""

from dataclasses import dataclass
from enum import StrEnum

from pyllmkit.domain.errors import DomainValidationError

from .definitions import Tool, validate_tool_name, validate_tool_set


class ToolChoiceKind(StrEnum):
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"
    SPECIFIC_TOOL = "specific_tool"


@dataclass(frozen=True, slots=True)
class ToolChoice:
    """Selection intent, not proof of TOOL_CALLING capability or execution."""

    kind: ToolChoiceKind
    name: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ToolChoiceKind:
            raise DomainValidationError("ToolChoice.kind must be ToolChoiceKind")
        if self.kind is ToolChoiceKind.SPECIFIC_TOOL:
            validate_tool_name(self.name)  # type: ignore[arg-type]
        elif self.name is not None:
            raise DomainValidationError("only SPECIFIC_TOOL may carry a name")

    @classmethod
    def specific(cls, name: str) -> "ToolChoice":
        return cls(ToolChoiceKind.SPECIFIC_TOOL, name)


def validate_tool_choice(choice: ToolChoice | None, tools: tuple[Tool, ...]) -> None:
    """Check local consistency without assuming a provider supports tools."""
    available = validate_tool_set(tools)
    if choice is None:
        return
    if type(choice) is not ToolChoice:
        raise DomainValidationError("choice must be ToolChoice or None")
    if choice.kind is ToolChoiceKind.REQUIRED and not available:
        raise DomainValidationError("REQUIRED needs at least one Tool")
    if choice.kind is ToolChoiceKind.SPECIFIC_TOOL and (
        choice.name not in {tool.name for tool in available}
    ):
        raise DomainValidationError("SPECIFIC_TOOL must refer to a declared Tool")
