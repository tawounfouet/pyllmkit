"""L4.1 tool declarations and local catalogue validation, without execution."""

from dataclasses import dataclass, field
from re import fullmatch

from pyllmkit.domain.errors import DomainValidationError

from .schema import ToolSchema


def validate_tool_name(name: str) -> str:
    """Stable ASCII-only local name; provider constraints are not inferred."""
    if type(name) is not str or fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) is None:
        raise DomainValidationError("Tool.name must be a 1..64 ASCII identifier")
    return name


@dataclass(frozen=True, slots=True)
class Tool:
    """Immutable description of a capability, never a Python callable."""

    name: str
    description: str | None
    schema: ToolSchema = field(repr=False)

    def __post_init__(self) -> None:
        validate_tool_name(self.name)
        if self.description is not None and (
            type(self.description) is not str or not self.description.strip()
        ):
            raise DomainValidationError("Tool.description must be nonblank or None")
        if type(self.schema) is not ToolSchema:
            raise DomainValidationError("Tool.schema must be a ToolSchema")


def validate_tool_set(tools: tuple[Tool, ...]) -> tuple[Tool, ...]:
    """Validate a local immutable catalogue and return it unchanged."""
    if type(tools) is not tuple or any(type(t) is not Tool for t in tools):
        raise DomainValidationError("tools must be tuple[Tool, ...]")
    names = [tool.name for tool in tools]
    if len(set(names)) != len(names):
        raise DomainValidationError("Tool names must be unique")
    return tools
