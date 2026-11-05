"""L2.3 ImageContent immutability and strict source typing."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError, Modality
from pyllmkit.domain.interactions import ContentPart, ImageContent, MediaSourceRef


def test_image_is_typed_content_part_with_m1_image_modality() -> None:
    ref = MediaSourceRef("asset", "img-123")
    image = ImageContent(source=ref)
    assert isinstance(image, ContentPart)
    assert image.source is ref
    assert image.kind == "image"
    assert image.modality == Modality("image")


def test_image_value_equality_frozen_hash_and_redacted_repr() -> None:
    ref = MediaSourceRef("uri", "https://example.org/img?token=secret")
    one = ImageContent(ref)
    two = ImageContent(MediaSourceRef("uri", ref.value))
    assert one == two
    assert hash(one) == hash(two)
    assert "secret" not in repr(one)
    with pytest.raises(FrozenInstanceError):
        one.source = MediaSourceRef("asset", "new")  # type: ignore[misc]


@pytest.mark.parametrize(
    "source",
    [None, "", "https://example.org/a.png", b"binary", {}, {"kind": "asset", "value": "id"}],
)
def test_image_requires_media_source_ref_without_implicit_conversion(source: object) -> None:
    with pytest.raises(DomainValidationError, match="ImageContent.source"):
        ImageContent(source=cast(MediaSourceRef, source))
