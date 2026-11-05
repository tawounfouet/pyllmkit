"""PIR2-03: the public Mapping annotation must match runtime behavior."""

from types import MappingProxyType
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
    message_from_dict,
    message_to_dict,
)


def _message() -> Message:
    return Message(
        Role.USER,
        Content((
            TextContent("Bonjour"),
            ImageContent(MediaSourceRef("asset", "media-id")),
            TextContent(""),
        )),
    )


def test_mapping_proxy_top_level_is_accepted_without_coercing_schema() -> None:
    payload = message_to_dict(_message())
    proxy = MappingProxyType(payload)
    assert message_from_dict(proxy) == _message()
    assert message_to_dict(message_from_dict(proxy)) == payload


def test_nested_readonly_mappings_work_recursively_and_preserve_order() -> None:
    original = _message()
    raw = message_to_dict(original)
    content = cast(dict[str, object], raw["content"])
    parts = cast(list[dict[str, object]], content["parts"])
    image = parts[1]
    image["source"] = MappingProxyType(cast(dict[str, object], image["source"]))
    content["parts"] = [
        MappingProxyType(item) for item in parts
    ]
    raw["content"] = MappingProxyType(content)
    assert message_from_dict(MappingProxyType(raw)) == original


def test_mapping_runtime_rejects_non_string_keys_and_unknown_fields_safely() -> None:
    raw = message_to_dict(_message())
    raw[cast(str, 123)] = "hidden-credential"
    with pytest.raises(DomainValidationError, match="string keys") as exc:
        message_from_dict(MappingProxyType(raw))
    assert "hidden-credential" not in str(exc.value)

    raw = message_to_dict(_message())
    raw["unreviewed_extra"] = "private-data"
    with pytest.raises(DomainValidationError, match="unknown fields") as exc:
        message_from_dict(MappingProxyType(raw))
    assert "private-data" not in str(exc.value)


@pytest.mark.parametrize("bad", [None, [], (), "{}", 5, False])
def test_non_mapping_payloads_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="object"):
        message_from_dict(cast(dict[str, object], bad))
