"""AC-006: build a valid offline, typed provider-agnostic text Message."""

from pyllmkit.domain import (
    Content,
    DomainValidationError,
    Message,
    Modality,
    Role,
    TextContent,
)
from pyllmkit.domain.interactions import Message as CanonicalMessage
from pyllmkit.domain.interactions import Role as CanonicalRole


def test_ac_006_public_text_message_without_provider_or_conversation() -> None:
    assert Message is CanonicalMessage
    assert Role is CanonicalRole
    message = Message(
        role=Role.USER,
        content=Content(parts=(TextContent("Bonjour"), TextContent(" PyLLMKit"))),
    )
    assert message.role is Role.USER
    assert tuple(part.kind for part in message.content.parts) == ("text", "text")
    assert tuple(part.modality for part in message.content.parts) == (
        Modality("text"),
        Modality("text"),
    )
    assert message.content.parts == (TextContent("Bonjour"), TextContent(" PyLLMKit"))
    assert issubclass(DomainValidationError, ValueError)
