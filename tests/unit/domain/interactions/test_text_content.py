"""L2.2 immutable TextContent and typed ContentPart contract."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError, Modality
from pyllmkit.domain.interactions import ContentPart, TextContent


def test_text_part_has_typed_kind_and_existing_modality() -> None:
    part = TextContent(text="Salut PyLLMKit")
    assert isinstance(part, ContentPart)
    assert part.text == "Salut PyLLMKit"
    assert part.kind == "text"
    assert part.modality == Modality("text")


def test_empty_text_is_intentional_valid_content() -> None:
    assert TextContent(text="").text == ""


@pytest.mark.parametrize("invalid", [None, 42, 3.14, b"bytes", {}, ["text"]])
def test_text_rejects_non_string_values(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="TextContent.text"):
        TextContent(text=cast(str, invalid))


def test_text_preserves_original_whitespace_unicode_and_newlines() -> None:
    raw = "  café \n 🐍  "
    assert TextContent(raw).text == raw


def test_text_content_value_equality_and_immutability() -> None:
    first = TextContent("same")
    assert first == TextContent("same")
    assert first != TextContent("other")
    with pytest.raises(FrozenInstanceError):
        first.text = "changed"  # type: ignore[misc]


def test_content_part_is_abstract_and_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        ContentPart()
