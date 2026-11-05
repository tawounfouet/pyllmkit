"""L2.2 API acceptance: imports and immutable ordered text content without SDKs."""

from pyllmkit.domain import Content, ContentPart, Modality, TextContent
from pyllmkit.domain.interactions import (
    Content as CanonicalContent,
)
from pyllmkit.domain.interactions import (
    TextContent as CanonicalTextContent,
)


def test_content_public_import_contract() -> None:
    assert Content is CanonicalContent
    assert TextContent is CanonicalTextContent
    sample = Content((TextContent("one"), TextContent("two"), TextContent("one")))
    assert all(isinstance(part, ContentPart) for part in sample.parts)
    assert tuple(part.text for part in sample.parts if isinstance(part, TextContent)) == (
        "one",
        "two",
        "one",
    )
    assert tuple(part.modality for part in sample.parts) == (Modality("text"),) * 3
