"""Minimal inference output Value Object, independent of provider wire formats."""

from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.interactions.media import MediaSourceRef


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


@dataclass(frozen=True, slots=True)
class ImageOutput:
    """Inference output representing a generated image."""

    media: MediaSourceRef
    mime_type: str = "image/png"
    width: int | None = None
    height: int | None = None
    revised_prompt: str | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("ImageOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("image/"):
            raise DomainValidationError("ImageOutput.mime_type must be a valid image MIME type")
        if self.width is not None and (type(self.width) is not int or self.width <= 0):
            raise DomainValidationError("ImageOutput.width must be a positive integer or None")
        if self.height is not None and (type(self.height) is not int or self.height <= 0):
            raise DomainValidationError("ImageOutput.height must be a positive integer or None")
        if self.revised_prompt is not None and type(self.revised_prompt) is not str:
            raise DomainValidationError("ImageOutput.revised_prompt must be a string or None")

    @property
    def kind(self) -> Literal["image"]:
        return "image"


@dataclass(frozen=True, slots=True)
class AudioOutput:
    """Inference output representing generated audio / speech."""

    media: MediaSourceRef
    mime_type: str = "audio/mpeg"
    duration_seconds: float | None = None
    transcript: str | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("AudioOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("audio/"):
            raise DomainValidationError("AudioOutput.mime_type must be a valid audio MIME type")
        if self.duration_seconds is not None and (
            not isinstance(self.duration_seconds, (int, float)) or self.duration_seconds < 0
        ):
            raise DomainValidationError("AudioOutput.duration_seconds must be a non-negative float or None")
        if self.transcript is not None and type(self.transcript) is not str:
            raise DomainValidationError("AudioOutput.transcript must be a string or None")

    @property
    def kind(self) -> Literal["audio"]:
        return "audio"


@dataclass(frozen=True, slots=True)
class VideoOutput:
    """Inference output representing a generated video."""

    media: MediaSourceRef
    mime_type: str = "video/mp4"
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None

    def __post_init__(self) -> None:
        if type(self.media) is not MediaSourceRef:
            raise DomainValidationError("VideoOutput.media must be a MediaSourceRef")
        if type(self.mime_type) is not str or not self.mime_type.startswith("video/"):
            raise DomainValidationError("VideoOutput.mime_type must be a valid video MIME type")
        if self.duration_seconds is not None and (
            not isinstance(self.duration_seconds, (int, float)) or self.duration_seconds < 0
        ):
            raise DomainValidationError("VideoOutput.duration_seconds must be a non-negative float or None")
        if self.width is not None and (type(self.width) is not int or self.width <= 0):
            raise DomainValidationError("VideoOutput.width must be a positive integer or None")
        if self.height is not None and (type(self.height) is not int or self.height <= 0):
            raise DomainValidationError("VideoOutput.height must be a positive integer or None")

    @property
    def kind(self) -> Literal["video"]:
        return "video"


SingleOutput: TypeAlias = TextOutput | ImageOutput | AudioOutput | VideoOutput


@dataclass(frozen=True, slots=True)
class MultiPartOutput:
    """Composite inference output holding multiple output parts."""

    parts: tuple[SingleOutput, ...]

    def __post_init__(self) -> None:
        if type(self.parts) is not tuple or not self.parts:
            raise DomainValidationError("MultiPartOutput.parts must be a non-empty tuple")
        for part in self.parts:
            if not isinstance(part, (TextOutput, ImageOutput, AudioOutput, VideoOutput)):
                raise DomainValidationError("MultiPartOutput.parts must contain valid output parts")

    @property
    def kind(self) -> Literal["multipart"]:
        return "multipart"


InferenceOutput: TypeAlias = SingleOutput | MultiPartOutput
