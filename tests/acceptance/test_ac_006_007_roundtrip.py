"""AC-006 and AC-007 reversible independent Interaction JSON v1 representation."""

import json

from pyllmkit.domain import (
    INTERACTION_SCHEMA_VERSION,
    Content,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
    message_from_dict,
    message_to_dict,
)


def test_ac_006_text_message_roundtrip_without_provider() -> None:
    original = Message(Role.USER, Content((TextContent(""), TextContent("Bonjour"))))
    payload = json.loads(json.dumps(message_to_dict(original), ensure_ascii=False))
    assert message_from_dict(payload) == original
    assert payload["schema_version"] == INTERACTION_SCHEMA_VERSION


def test_ac_007_text_image_text_and_asset_roundtrip() -> None:
    original = Message(
        Role.USER,
        Content((
            TextContent("Regarde "),
            ImageContent(MediaSourceRef("asset", "image-123")),
            TextContent(" et décris 🐍"),
        )),
    )
    payload = json.loads(json.dumps(message_to_dict(original), ensure_ascii=False))
    recovered = message_from_dict(payload)
    assert recovered == original
    assert tuple(part.kind for part in recovered.content.parts) == ("text", "image", "text")


def test_ac_007_uri_image_roundtrip_without_fetch() -> None:
    original = Message(
        Role.USER,
        Content((ImageContent(MediaSourceRef("uri", "https://example.org/img.png")),)),
    )
    assert message_from_dict(json.loads(json.dumps(message_to_dict(original)))) == original
