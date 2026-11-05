"""L2.2 ordered non-empty Content, with no implicit list/string coercion."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.interactions import Content, ContentPart, TextContent


def test_content_retains_exact_order_and_duplicate_values() -> None:
    a, b = TextContent("first"), TextContent("second")
    content = Content(parts=(a, b, a))
    assert content.parts == (a, b, a)
    assert len(content.parts) == 3
    assert content.parts[0] is content.parts[2]


def test_content_has_value_equality_and_immutable_tuple() -> None:
    one = Content((TextContent("one"), TextContent("two")))
    two = Content((TextContent("one"), TextContent("two")))
    assert one == two
    assert hash(one) == hash(two)
    with pytest.raises(FrozenInstanceError):
        one.parts = ()  # type: ignore[misc]


def test_empty_text_part_is_not_the_same_as_empty_content() -> None:
    assert Content((TextContent(""),)).parts[0].text == ""
    with pytest.raises(DomainValidationError, match="non-empty"):
        Content(())


@pytest.mark.parametrize("invalid", [None, "", "text", [], [TextContent("x")], {}, 2])
def test_content_requires_non_empty_tuple(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="non-empty tuple"):
        Content(cast(tuple[ContentPart, ...], invalid))


@pytest.mark.parametrize("invalid", [None, "text", 123, {}, ("text",)])
def test_content_rejects_untyped_parts(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="ContentPart"):
        Content(cast(tuple[ContentPart, ...], (TextContent("ok"), invalid)))


def test_existing_modality_is_not_rewritten_or_negotiated() -> None:
    content = Content((TextContent("abc"), TextContent("abc")))
    assert [part.modality.value for part in content.parts] == ["text", "text"]
    assert [part.kind for part in content.parts] == ["text", "text"]
