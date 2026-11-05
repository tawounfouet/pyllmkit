"""L2.1 Message Value Object semantics, strict role and content composition."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.interactions import Content, Message, Role, TextContent


def _content() -> Content:
    return Content((TextContent("Bonjour"), TextContent(" PyLLMKit")))


@pytest.mark.parametrize("role", list(Role))
def test_each_canonical_role_constructs_a_message(role: Role) -> None:
    msg = Message(role=role, content=_content())
    assert msg.role is role
    assert msg.content.parts[0] == TextContent("Bonjour")


def test_tool_speaker_role_does_not_trigger_tool_execution() -> None:
    msg = Message(Role.TOOL, Content((TextContent("result"),)))
    assert msg.role == Role.TOOL
    assert msg.content.parts[0].kind == "text"


def test_message_is_immutable_and_equal_by_value() -> None:
    first = Message(Role.USER, _content())
    second = Message(Role.USER, _content())
    assert first == second
    assert hash(first) == hash(second)
    assert first != Message(Role.ASSISTANT, _content())
    with pytest.raises(FrozenInstanceError):
        first.role = Role.ASSISTANT  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.content = Content((TextContent("changed"),))  # type: ignore[misc]


@pytest.mark.parametrize("bad", ["user", "USER", "", None, 3, {}])
def test_invalid_or_implicit_role_is_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="Message.role"):
        Message(role=cast(Role, bad), content=_content())


@pytest.mark.parametrize("bad", ["hi", ["message"], (), None, 42, {}])
def test_message_requires_a_content_value_object(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="Message.content"):
        Message(role=Role.USER, content=cast(Content, bad))


def test_missing_role_or_content_is_a_constructor_error() -> None:
    with pytest.raises(TypeError):
        Message(role=Role.USER)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Message(content=_content())  # type: ignore[call-arg]


def test_a_sequence_of_messages_is_ordered_without_conversation() -> None:
    messages = (
        Message(Role.SYSTEM, Content((TextContent("instruction"),))),
        Message(Role.USER, Content((TextContent("question"),))),
        Message(Role.ASSISTANT, Content((TextContent("answer"),))),
    )
    assert tuple(msg.role for msg in messages) == (Role.SYSTEM, Role.USER, Role.ASSISTANT)
