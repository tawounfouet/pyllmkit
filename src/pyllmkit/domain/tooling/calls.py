"""Tool calls are identity-based descriptions; results are immutable observations."""

from dataclasses import dataclass, field

from pyllmkit.domain.errors import DomainValidationError

from .arguments import ToolArguments
from .definitions import validate_tool_name
from .identifiers import ToolCallId
from .json_values import FrozenJSON, freeze_json, thaw_json


@dataclass(frozen=True, slots=True, eq=False)
class ToolCall:
    """Identity-based Entity that cannot invoke or execute a function."""

    call_id: ToolCallId
    tool_name: str
    arguments: ToolArguments = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.call_id) is not ToolCallId:
            raise DomainValidationError("ToolCall.call_id must be ToolCallId")
        validate_tool_name(self.tool_name)
        if type(self.arguments) is not ToolArguments:
            raise DomainValidationError("ToolCall.arguments must be ToolArguments")

    def __eq__(self, other: object) -> bool:
        if type(other) is not ToolCall:
            return NotImplemented
        return self.call_id == other.call_id

    def __hash__(self) -> int:
        return hash(self.call_id)


@dataclass(frozen=True, slots=True, init=False)
class ToolResult:
    """One caller-supplied JSON result, success or explicit failure."""

    call_id: ToolCallId
    is_error: bool
    _frozen: FrozenJSON = field(repr=False)

    def __init__(self, call_id: ToolCallId, value: object, is_error: bool = False) -> None:
        if type(call_id) is not ToolCallId:
            raise DomainValidationError("ToolResult.call_id must be ToolCallId")
        if type(is_error) is not bool:
            raise DomainValidationError("ToolResult.is_error must be a boolean")
        frozen = freeze_json(value)
        object.__setattr__(self, "call_id", call_id)
        object.__setattr__(self, "is_error", is_error)
        object.__setattr__(self, "_frozen", frozen)

    @property
    def value(self) -> object:
        """Return a defensive JSON tree, never a mutable internal reference."""
        return thaw_json(self._frozen)
