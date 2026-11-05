"""Minimal inference output Value Object, independent of provider wire formats."""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from pyllmkit.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class TextOutput:
    """Literal text, including the empty string; never provider-native payload."""

    text: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.text) is not str:
            raise DomainValidationError("TextOutput.text must be a string")

    @property
    def kind(self) -> Literal["text"]:
        return "text"


# Only one output variant is supported in a3. A future variant requires an ADR
# and an independent versioned codec extension; this alias is not a runtime base.
InferenceOutput: TypeAlias = TextOutput
