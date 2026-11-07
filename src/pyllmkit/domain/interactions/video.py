"""Immutable video content referencing passive media, never inline bytes."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality

from .media import MediaSourceRef
from .parts import ContentPart


@dataclass(frozen=True, slots=True)
class VideoContent(ContentPart):
    """A video reference, not a request to decode or stream media."""

    source: MediaSourceRef
    format: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, MediaSourceRef):
            raise DomainValidationError("VideoContent.source must be a MediaSourceRef")
        if self.format is not None:
            if not isinstance(self.format, str) or not self.format.strip():
                raise DomainValidationError("VideoContent.format must be a nonblank string or None")

    @property
    def kind(self) -> str:
        """Stable domain discriminator for the codec."""
        return "video"

    @property
    def modality(self) -> Modality:
        """Describe the part modality."""
        return Modality("video")

