"""VideoContent immutability, format validation, and strict source typing."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError, Modality
from pyllmkit.domain.interactions import ContentPart, MediaSourceRef, VideoContent


def test_video_is_typed_content_part_with_m1_video_modality() -> None:
    ref = MediaSourceRef("asset", "video-123")
    video = VideoContent(source=ref, format="mp4")
    assert isinstance(video, ContentPart)
    assert video.source is ref
    assert video.format == "mp4"
    assert video.kind == "video"
    assert video.modality == Modality("video")


def test_video_value_equality_frozen_hash_and_redacted_repr() -> None:
    ref = MediaSourceRef("uri", "https://example.org/clip.mov?token=secret")
    one = VideoContent(ref, format="mov")
    two = VideoContent(MediaSourceRef("uri", ref.value), format="mov")
    assert one == two
    assert hash(one) == hash(two)
    assert "secret" not in repr(one)
    with pytest.raises(FrozenInstanceError):
        one.source = MediaSourceRef("asset", "new")  # type: ignore[misc]


def test_video_optional_format_and_validation() -> None:
    ref = MediaSourceRef("asset", "video-456")
    video = VideoContent(ref)
    assert video.format is None

    with pytest.raises(DomainValidationError, match="VideoContent.format"):
        VideoContent(ref, format="")
    with pytest.raises(DomainValidationError, match="VideoContent.format"):
        VideoContent(ref, format="   ")
    with pytest.raises(DomainValidationError, match="VideoContent.format"):
        VideoContent(ref, format=cast(str, 123))


@pytest.mark.parametrize(
    "source",
    [None, "", "https://example.org/a.mp4", b"binary", {}, {"kind": "asset", "value": "id"}],
)
def test_video_requires_media_source_ref_without_implicit_conversion(source: object) -> None:
    with pytest.raises(DomainValidationError, match="VideoContent.source"):
        VideoContent(source=cast(MediaSourceRef, source))

