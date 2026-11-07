"""Immutable audio content referencing passive media, never inline bytes."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality

from .media import MediaSourceRef
from .parts import ContentPart


@dataclass(frozen=True, slots=True)
class AudioContent(ContentPart):
    """An audio reference, not a request to decode or transcode media."""

    source: MediaSourceRef
    format: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, MediaSourceRef):
            raise DomainValidationError("AudioContent.source must be a MediaSourceRef")
        if self.format is not None:
            if not isinstance(self.format, str) or not self.format.strip():
                raise DomainValidationError("AudioContent.format must be a nonblank string or None")

    @property
    def kind(self) -> str:
        """Stable domain discriminator for the codec."""
        return "audio"

    @property
    def modality(self) -> Modality:
        """Describe the part modality."""
        return Modality("audio")

