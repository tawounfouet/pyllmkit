"""AC-007: typed text-image-text Message with exact ordered content and no I/O."""

from pyllmkit.domain import (
    Content,
    ContentPart,
    ImageContent,
    MediaSourceRef,
    Message,
    Modality,
    Role,
    TextContent,
)
from pyllmkit.domain.interactions import (
    ImageContent as CanonicalImageContent,
)
from pyllmkit.domain.interactions import (
    MediaSourceRef as CanonicalMediaSourceRef,
)


def test_ac_007_provider_free_message_keeps_text_image_text_order() -> None:
    assert ImageContent is CanonicalImageContent
    assert MediaSourceRef is CanonicalMediaSourceRef
    image = ImageContent(source=MediaSourceRef("asset", "image-123"))
    parts: tuple[ContentPart, ...] = (
        TextContent("Décris cette image : "),
        image,
        TextContent(" avec précision."),
    )
    message = Message(role=Role.USER, content=Content(parts=parts))

    assert message.content.parts == parts
    assert tuple(part.kind for part in message.content.parts) == ("text", "image", "text")
    assert tuple(part.modality for part in message.content.parts) == (
        Modality("text"),
        Modality("image"),
        Modality("text"),
    )
    assert message.content.parts[1] is image
    assert message.content.parts[0] == TextContent("Décris cette image : ")
    assert message.content.parts[2] == TextContent(" avec précision.")


def test_ac_007_preserves_duplicate_images_and_empty_text() -> None:
    image = ImageContent(MediaSourceRef("uri", "https://example.org/assets/1.png"))
    message = Message(Role.USER, Content((TextContent(""), image, image, TextContent(""))))
    assert message.content.parts[1] is message.content.parts[2]
    assert len(message.content.parts) == 4
    assert message.content.parts[0] == TextContent("")
    assert message.content.parts[-1] == TextContent("")


def test_ac_006_text_message_still_works_with_new_image_type() -> None:
    message = Message(Role.ASSISTANT, Content((TextContent("Bonjour"),)))
    assert tuple(part.kind for part in message.content.parts) == ("text",)
