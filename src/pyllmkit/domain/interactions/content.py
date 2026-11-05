"""Ordered content value object with strict structural validation."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .parts import ContentPart


@dataclass(frozen=True, slots=True)
class Content:
    """One or more ordered content parts; preserves duplicate parts (INT-003/005)."""

    parts: tuple[ContentPart, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.parts, tuple) or not self.parts:
            raise DomainValidationError("Content.parts must be a non-empty tuple")
        if any(not isinstance(part, ContentPart) for part in self.parts):
            raise DomainValidationError("Content.parts must contain only ContentPart values")
