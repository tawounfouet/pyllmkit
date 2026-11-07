"""AudioContent immutability, format validation, and strict source typing."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError, Modality
from pyllmkit.domain.interactions import AudioContent, ContentPart, MediaSourceRef


def test_audio_is_typed_content_part_with_m1_audio_modality() -> None:
    ref = MediaSourceRef("asset", "audio-123")
    audio = AudioContent(source=ref, format="mp3")
    assert isinstance(audio, ContentPart)
    assert audio.source is ref
    assert audio.format == "mp3"
    assert audio.kind == "audio"
    assert audio.modality == Modality("audio")


def test_audio_value_equality_frozen_hash_and_redacted_repr() -> None:
    ref = MediaSourceRef("uri", "https://example.org/sound.wav?token=secret")
    one = AudioContent(ref, format="wav")
    two = AudioContent(MediaSourceRef("uri", ref.value), format="wav")
    assert one == two
    assert hash(one) == hash(two)
    assert "secret" not in repr(one)
    with pytest.raises(FrozenInstanceError):
        one.source = MediaSourceRef("asset", "new")  # type: ignore[misc]


def test_audio_optional_format_and_validation() -> None:
    ref = MediaSourceRef("asset", "audio-456")
    audio = AudioContent(ref)
    assert audio.format is None

    with pytest.raises(DomainValidationError, match="AudioContent.format"):
        AudioContent(ref, format="")
    with pytest.raises(DomainValidationError, match="AudioContent.format"):
        AudioContent(ref, format="   ")
    with pytest.raises(DomainValidationError, match="AudioContent.format"):
        AudioContent(ref, format=cast(str, 123))


@pytest.mark.parametrize(
    "source",
    [None, "", "https://example.org/a.mp3", b"binary", {}, {"kind": "asset", "value": "id"}],
)
def test_audio_requires_media_source_ref_without_implicit_conversion(source: object) -> None:
    with pytest.raises(DomainValidationError, match="AudioContent.source"):
        AudioContent(source=cast(MediaSourceRef, source))

