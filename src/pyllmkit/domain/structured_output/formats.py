"""Three explicit response format contracts without provider capability assumptions."""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.tooling.schema import ToolSchema


@dataclass(frozen=True, slots=True)
class TextResponseFormat:
    """Unstructured, free-form text. No JSON or schema guarantee."""

    @property
    def kind(self) -> Literal["text"]:
        return "text"


@dataclass(frozen=True, slots=True)
class JsonResponseFormat:
    """JSON expected, but no validation evidence implied by this request."""

    strict: bool | None = None

    def __post_init__(self) -> None:
        if self.strict is not None and type(self.strict) is not bool:
            raise DomainValidationError("JsonResponseFormat.strict must be bool or None")

    @property
    def kind(self) -> Literal["json"]:
        return "json"


@dataclass(frozen=True, slots=True)
class SchemaResponseFormat:
    """An approved P4-JSON-1 instance-validation contract."""

    schema: ToolSchema = field(repr=False)
    strict: bool | None = None

    def __post_init__(self) -> None:
        if type(self.schema) is not ToolSchema:
            raise DomainValidationError("SchemaResponseFormat.schema must be ToolSchema")
        if self.strict is not None and type(self.strict) is not bool:
            raise DomainValidationError("SchemaResponseFormat.strict must be bool or None")

    @property
    def kind(self) -> Literal["json_schema"]:
        return "json_schema"


ResponseFormat: TypeAlias = TextResponseFormat | JsonResponseFormat | SchemaResponseFormat
