"""Immutable text-content value object (INT-008, MOD-003, ADR-010)."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality

from .parts import ContentPart


@dataclass(frozen=True, slots=True)
class TextContent(ContentPart):
    """One text content part. Intentional empty text is valid, None is not."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise DomainValidationError("TextContent.text must be a string")

    @property
    def kind(self) -> str:
        """Canonical part discriminator, distinct from provider wire formats."""
        return "text"

    @property
    def modality(self) -> Modality:
        """Return the Phase 1 canonical text modality."""
        return Modality("text")
