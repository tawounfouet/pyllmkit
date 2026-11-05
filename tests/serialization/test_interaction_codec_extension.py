"""Codec refuses unreviewed ContentPart extensions even when Domain permits them."""

from dataclasses import dataclass

import pytest

from pyllmkit.domain import Content, DomainValidationError, Message, Modality, Role
from pyllmkit.domain.interactions import ContentPart
from pyllmkit.domain.interactions.serialization import message_to_dict


@dataclass(frozen=True, slots=True)
class FutureAudioContent(ContentPart):
    """Test-only extension; not a published PyLLMKit audio type."""

    value: str

    @property
    def kind(self) -> str:
        return "audio"

    @property
    def modality(self) -> Modality:
        return Modality("audio")


def test_unapproved_part_extension_is_not_silently_serialized() -> None:
    message = Message(Role.USER, Content((FutureAudioContent("opaque"),)))
    with pytest.raises(DomainValidationError, match="unsupported Interaction content part"):
        message_to_dict(message)
