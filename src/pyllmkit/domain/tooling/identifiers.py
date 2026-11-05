"""Explicit local call identity, independent of provider formats and execution."""

from dataclasses import dataclass, field

from pyllmkit.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class ToolCallId:
    """Opaque, case-sensitive, caller-supplied identifier (ADR-023)."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.strip() or len(self.value) > 256:
            raise DomainValidationError("ToolCallId must be a nonblank string of at most 256 chars")

    def __str__(self) -> str:
        return self.value
