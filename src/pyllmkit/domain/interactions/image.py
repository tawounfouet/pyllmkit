"""Immutable image content referencing passive media, never inline bytes."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality

from .media import MediaSourceRef
from .parts import ContentPart


@dataclass(frozen=True, slots=True)
class ImageContent(ContentPart):
    """An image reference, not a request to download, decode or OCR media."""

    source: MediaSourceRef

    def __post_init__(self) -> None:
        if not isinstance(self.source, MediaSourceRef):
            raise DomainValidationError("ImageContent.source must be a MediaSourceRef")

    @property
    def kind(self) -> str:
        """Stable domain discriminator for the future explicit codec."""
        return "image"

    @property
    def modality(self) -> Modality:
        """Describe the part, not Model/Deployment vision support."""
        return Modality("image")
