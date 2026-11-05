"""ADR-012 strict versioned Interaction mapping and JSON round-trip tests."""

import json
from copy import deepcopy
from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    DomainValidationError,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
)
from pyllmkit.domain.interactions import INTERACTION_SCHEMA_VERSION
from pyllmkit.domain.interactions.serialization import message_from_dict, message_to_dict


def _multimodal_message() -> Message:
    image = ImageContent(MediaSourceRef("uri", "https://example.org/a.png?token=private"))
    return Message(
        role=Role.USER,
        content=Content((
            TextContent("  café 🐍\n"),
            image,
            TextContent(""),
            image,
            TextContent("  fin"),
        )),
    )


def _valid_payload() -> dict[str, object]:
    return message_to_dict(_multimodal_message())


def _parts(payload: dict[str, object]) -> list[dict[str, object]]:
    content = cast(dict[str, object], payload["content"])
    return cast(list[dict[str, object]], content["parts"])


def test_schema_one_canonical_shape_and_public_constant() -> None:
    message = Message(Role.USER, Content((TextContent("Bonjour"),)))
    assert INTERACTION_SCHEMA_VERSION == 1
    assert message_to_dict(message) == {
        "schema_version": 1,
        "object_type": "message",
        "role": "user",
        "content": {"parts": [{"kind": "text", "text": "Bonjour"}]},
    }


@pytest.mark.parametrize("role", list(Role))
def test_all_five_canonical_roles_round_trip(role: Role) -> None:
    original = Message(role, Content((TextContent("text"),)))
    assert message_from_dict(message_to_dict(original)) == original


def test_text_json_round_trip_preserves_empty_and_unicode_exactly() -> None:
    original = Message(Role.ASSISTANT, Content((TextContent(""), TextContent("été 🐍\n  "))))
    payload = json.loads(json.dumps(message_to_dict(original), ensure_ascii=False))
    assert message_from_dict(payload) == original
    assert message_to_dict(message_from_dict(payload)) == payload


def test_multimodal_json_round_trip_preserves_kind_order_and_duplicates() -> None:
    original = _multimodal_message()
    payload = json.loads(json.dumps(message_to_dict(original), ensure_ascii=False))
    decoded = message_from_dict(payload)
    assert decoded == original
    assert message_to_dict(decoded) == payload
    assert tuple(part.kind for part in decoded.content.parts) == (
        "text", "image", "text", "image", "text"
    )
    assert decoded.content.parts[1] == decoded.content.parts[3]
    assert decoded.content.parts[0] == TextContent("  café 🐍\n")
    image = decoded.content.parts[1]
    assert isinstance(image, ImageContent)
    assert image.source.value == "https://example.org/a.png?token=private"


@pytest.mark.parametrize("kind,value", [
    ("uri", "https://example.org/picture.png?a=1&b=2"),
    ("asset", " asset:opaque-123 "),
])
def test_both_passive_media_source_kinds_round_trip(kind: str, value: str) -> None:
    original = Message(Role.USER, Content((ImageContent(MediaSourceRef(kind, value)),)))
    decoded = message_from_dict(json.loads(json.dumps(message_to_dict(original))))
    assert decoded == original
    assert decoded.content.parts[0].modality.value == "image"


@pytest.mark.parametrize("bad", [None, "", [], (), 1, False, "{}", {"role": "user"}])
def test_decoder_rejects_non_message_or_incomplete_payload(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        message_from_dict(cast(dict[str, object], bad))


@pytest.mark.parametrize("bad", [None, "1", 1.0, 0, 2, True, False, [], {}])
def test_invalid_schema_version_rejected_without_bool_int_confusion(bad: object) -> None:
    raw = _valid_payload()
    raw["schema_version"] = bad
    with pytest.raises(DomainValidationError, match="schema_version"):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", ["reply", "tool", "Message", "", None, {}, 1])
def test_invalid_object_type_rejected(bad: object) -> None:
    raw = _valid_payload()
    raw["object_type"] = bad
    with pytest.raises(DomainValidationError, match="object_type"):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", ["USER", "human", "moderator", "", None, {}, True, 4])
def test_invalid_role_rejected(bad: object) -> None:
    raw = _valid_payload()
    raw["role"] = bad
    with pytest.raises(DomainValidationError):
        message_from_dict(raw)


def test_unknown_root_field_rejected_without_echoing_field_or_value() -> None:
    raw = _valid_payload()
    raw["private_secret_key"] = "password123"
    with pytest.raises(DomainValidationError) as err:
        message_from_dict(raw)
    assert "private_secret_key" not in str(err.value)
    assert "password123" not in str(err.value)


def test_unknown_and_missing_content_fields_rejected() -> None:
    raw = _valid_payload()
    content = cast(dict[str, object], raw["content"])
    content["extra"] = True
    with pytest.raises(DomainValidationError, match="content contains unknown"):
        message_from_dict(raw)
    del content["extra"]
    del content["parts"]
    with pytest.raises(DomainValidationError, match="missing required"):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", [None, (), {}, "", "text", [], [None], [{}], ["text"]])
def test_non_array_empty_or_malformed_parts_rejected(bad: object) -> None:
    raw = _valid_payload()
    cast(dict[str, object], raw["content"])["parts"] = bad
    with pytest.raises(DomainValidationError):
        message_from_dict(raw)


def test_unknown_text_and_image_part_fields_rejected() -> None:
    raw = _valid_payload()
    parts = _parts(raw)
    parts[0]["provider_payload"] = {"secret": "do-not-log"}
    with pytest.raises(DomainValidationError, match="unknown fields"):
        message_from_dict(raw)
    del parts[0]["provider_payload"]
    parts[1]["provider_payload"] = {"secret": "do-not-log"}
    with pytest.raises(DomainValidationError, match="unknown fields"):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", ["audio", "document", "tool_call", "unknown", None, 3])
def test_unsupported_part_kind_rejected(bad: object) -> None:
    raw = _valid_payload()
    _parts(raw)[0]["kind"] = bad
    with pytest.raises(DomainValidationError):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", [None, 8, False, {}, []])
def test_non_string_text_rejected_but_intentional_empty_is_valid(bad: object) -> None:
    raw = message_to_dict(Message(Role.USER, Content((TextContent(""),))))
    assert message_from_dict(raw).content.parts[0] == TextContent("")
    _parts(raw)[0]["text"] = bad
    with pytest.raises(DomainValidationError, match="text"):
        message_from_dict(raw)


@pytest.mark.parametrize("bad", [None, {}, [], False, 3, "", "https://example.org/a.png"])
def test_image_source_must_be_object_with_exact_fields(bad: object) -> None:
    raw = _valid_payload()
    _parts(raw)[1]["source"] = bad
    with pytest.raises(DomainValidationError):
        message_from_dict(raw)


def test_source_unknown_field_rejected_and_missing_field_rejected() -> None:
    raw = _valid_payload()
    source = cast(dict[str, object], _parts(raw)[1]["source"])
    source["url"] = "file:///secret"
    with pytest.raises(DomainValidationError, match="unknown"):
        message_from_dict(raw)
    del source["url"]
    del source["value"]
    with pytest.raises(DomainValidationError, match="missing"):
        message_from_dict(raw)


@pytest.mark.parametrize("kind,value", [
    ("file", "file:///tmp/image.png"),
    ("data", "data:image/png;base64,AAAA"),
    ("uri", "file:///etc/passwd"),
    ("uri", "https:///missing-host"),
    ("asset", ""),
    ("asset", "   "),
    ("uri", 42),
    ("asset", None),
    (None, "id"),
])
def test_source_validation_rejects_invalid_types_and_values(kind: object, value: object) -> None:
    raw = _valid_payload()
    source = cast(dict[str, object], _parts(raw)[1]["source"])
    source["kind"] = kind
    source["value"] = value
    with pytest.raises(DomainValidationError):
        message_from_dict(raw)


def test_source_secret_does_not_appear_in_decoder_validation_errors() -> None:
    raw = _valid_payload()
    source = cast(dict[str, object], _parts(raw)[1]["source"])
    source["value"] = "file:///etc/passwd?api_key=sensitive"
    with pytest.raises(DomainValidationError) as exc:
        message_from_dict(raw)
    assert "sensitive" not in str(exc.value)


def test_input_data_not_mutated_and_output_has_fresh_containers() -> None:
    raw = _valid_payload()
    before = deepcopy(raw)
    decoded = message_from_dict(raw)
    assert raw == before
    encoded = message_to_dict(decoded)
    assert encoded == raw
    assert encoded is not raw
    assert encoded["content"] is not raw["content"]


def test_encoder_rejects_untyped_input() -> None:
    with pytest.raises(DomainValidationError, match="expects a Message"):
        message_to_dict(cast(Message, {"role": "user"}))


def test_decoder_rejects_non_string_mapping_keys() -> None:
    raw = _valid_payload()
    raw[cast(str, 42)] = "bad-key"
    with pytest.raises(DomainValidationError, match="string keys"):
        message_from_dict(raw)
