"""ADR-014: request is an immutable intent, not an execution or conversation."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    DomainValidationError,
    ImageContent,
    MediaSourceRef,
    Message,
    ModelId,
    Role,
    TextContent,
)
from pyllmkit.domain.inference import GenerationConfig, InferenceRequest, ModelTarget


def _message() -> Message:
    return Message(Role.USER, Content((TextContent("Bonjour"),)))


def test_value_object_preserves_message_order_and_duplicates() -> None:
    system = Message(Role.SYSTEM, Content((TextContent("System"),)))
    user = _message()
    request = InferenceRequest(
        target=ModelTarget(ModelId("model")),
        messages=(system, user, user),
        generation_config=GenerationConfig(temperature=0.0),
    )
    assert tuple(x.role for x in request.messages) == (Role.SYSTEM, Role.USER, Role.USER)
    assert request.messages[1] is request.messages[2]
    equal_value = InferenceRequest(
        target=ModelTarget(ModelId("model")),
        messages=(system, user, user),
        generation_config=GenerationConfig(temperature=0.0),
    )
    assert request == equal_value
    assert hash(request) == hash(equal_value)
    assert request != InferenceRequest(ModelTarget(ModelId("model2")), (system, user, user))


def test_multimodal_request_preserves_parts_and_does_not_claim_vision_support() -> None:
    parts = (
        TextContent("Explain:"),
        ImageContent(MediaSourceRef("asset", "photo-1")),
        TextContent(" in detail"),
    )
    message = Message(Role.USER, Content(parts))
    request = InferenceRequest(ModelTarget(ModelId("unknown-model")), (message,))
    assert request.messages[0].content.parts == parts
    assert tuple(part.kind for part in request.messages[0].content.parts) == (
        "text", "image", "text",
    )
    assert request.generation_config is None


@pytest.mark.parametrize(
    ("target", "messages", "config"),
    [
        (None, (_message(),), None),
        ("model", (_message(),), None),
        (ModelId("model"), (_message(),), None),
        (ModelTarget(ModelId("model")), (), None),
        (ModelTarget(ModelId("model")), [], None),
        (ModelTarget(ModelId("model")), [_message()], None),
        (ModelTarget(ModelId("model")), (_message(), "message"), None),
        (ModelTarget(ModelId("model")), (_message(),), {}),
        (ModelTarget(ModelId("model")), (_message(),), 1),
    ],
)
def test_bad_request_structure_is_rejected(
    target: object, messages: object, config: object
) -> None:
    with pytest.raises(DomainValidationError):
        InferenceRequest(
            cast(ModelTarget, target),
            cast(tuple[Message, ...], messages),
            cast(GenerationConfig | None, config),
        )


def test_request_is_immutable_without_a_generated_id() -> None:
    request = InferenceRequest(ModelTarget(ModelId("example")), (_message(),))
    assert not hasattr(request, "id")
    assert not hasattr(request, "provider")
    with pytest.raises(FrozenInstanceError):
        request.messages = ()  # type: ignore[misc]
