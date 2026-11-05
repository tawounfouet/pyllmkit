"""AC-007: build a text-image-text Message without network, provider or codec."""

from pyllmkit.domain import Content, ImageContent, MediaSourceRef, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(
        parts=(
            TextContent("Regarde : "),
            ImageContent(source=MediaSourceRef("asset", "image-123")),
            TextContent(" Que vois-tu ?"),
        )
    ),
)

assert tuple(part.kind for part in message.content.parts) == ("text", "image", "text")
assert tuple(part.modality.value for part in message.content.parts) == (
    "text",
    "image",
    "text",
)
print("AC-007 multimodal Message: OK")
