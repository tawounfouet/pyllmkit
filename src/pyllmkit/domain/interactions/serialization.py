"""Strict independent Interaction Domain JSON-compatible codec (ADR-012).

Only Message, TextContent and ImageContent belong to schema version 1.
Decoding never fetches media or imports provider services.
"""

from collections.abc import Mapping
from typing import cast

from pyllmkit.domain.errors import DomainValidationError

from .audio import AudioContent
from .content import Content
from .image import ImageContent
from .media import MediaSourceRef
from .message import Message
from .parts import ContentPart
from .roles import Role
from .text import TextContent
from .video import VideoContent

INTERACTION_SCHEMA_VERSION = 1

_MESSAGE_FIELDS = frozenset({"schema_version", "object_type", "role", "content"})
_CONTENT_FIELDS = frozenset({"parts"})
_TEXT_FIELDS = frozenset({"kind", "text"})
_IMAGE_FIELDS = frozenset({"kind", "source"})
_AUDIO_FIELDS = frozenset({"kind", "source"})
_AUDIO_OPTIONAL_FIELDS = frozenset({"kind", "source", "format"})
_VIDEO_FIELDS = frozenset({"kind", "source"})
_VIDEO_OPTIONAL_FIELDS = frozenset({"kind", "source", "format"})
_SOURCE_FIELDS = frozenset({"kind", "value"})


def _object(value: object, label: str) -> Mapping[str, object]:
    """Accept Mapping inputs while validating string-key JSON object semantics.

    No conversion/copy of values is performed; a MappingProxyType is supported.
    Lists and other non-mapping containers are never coerced to objects.
    """
    if not isinstance(value, Mapping) or any(type(k) is not str for k in value):
        raise DomainValidationError(f"{label} must be an object with string keys")
    return cast(Mapping[str, object], value)


def _exact_fields(data: Mapping[str, object], fields: frozenset[str], label: str) -> None:
    """Reject missing/extra keys without echoing untrusted keys or values."""
    present = set(data)
    if present - fields:
        raise DomainValidationError(f"{label} contains unknown fields")
    if fields - present:
        raise DomainValidationError(f"{label} is missing required fields")


def _validate_fields(
    data: Mapping[str, object],
    required: frozenset[str],
    allowed: frozenset[str],
    label: str,
) -> None:
    """Reject missing required keys or unknown keys."""
    present = set(data)
    if present - allowed:
        raise DomainValidationError(f"{label} contains unknown fields")
    if required - present:
        raise DomainValidationError(f"{label} is missing required fields")


def _string(data: Mapping[str, object], field: str, label: str) -> str:
    """Accept an actual JSON string, never null or an implicit cast."""
    value = data[field]
    if type(value) is not str:
        raise DomainValidationError(f"{label}.{field} must be a string")
    return value


def _part_to_dict(part: ContentPart) -> dict[str, object]:
    """Encode only concrete types approved for schema version 1."""
    if type(part) is TextContent:
        return {"kind": "text", "text": part.text}
    if type(part) is ImageContent:
        return {
            "kind": "image",
            "source": {"kind": part.source.kind, "value": part.source.value},
        }
    if type(part) is AudioContent:
        result: dict[str, object] = {
            "kind": "audio",
            "source": {"kind": part.source.kind, "value": part.source.value},
        }
        if part.format is not None:
            result["format"] = part.format
        return result
    if type(part) is VideoContent:
        result = {
            "kind": "video",
            "source": {"kind": part.source.kind, "value": part.source.value},
        }
        if part.format is not None:
            result["format"] = part.format
        return result
    raise DomainValidationError("unsupported Interaction content part type")


def _part_from_dict(raw: object) -> ContentPart:
    data = _object(raw, "part")
    if "kind" not in data:
        raise DomainValidationError("part is missing required fields")
    kind = _string(data, "kind", "part")
    if kind == "text":
        _exact_fields(data, _TEXT_FIELDS, "text part")
        return TextContent(text=_string(data, "text", "text part"))
    if kind == "image":
        _exact_fields(data, _IMAGE_FIELDS, "image part")
        source = _object(data["source"], "image source")
        _exact_fields(source, _SOURCE_FIELDS, "image source")
        return ImageContent(
            source=MediaSourceRef(
                kind=_string(source, "kind", "image source"),
                value=_string(source, "value", "image source"),
            )
        )
    if kind == "audio":
        _validate_fields(data, _AUDIO_FIELDS, _AUDIO_OPTIONAL_FIELDS, "audio part")
        source = _object(data["source"], "audio source")
        _exact_fields(source, _SOURCE_FIELDS, "audio source")
        raw_format = data.get("format")
        fmt: str | None = None
        if raw_format is not None:
            if type(raw_format) is not str or not raw_format.strip():
                raise DomainValidationError("audio part.format must be a nonblank string or null")
            fmt = raw_format
        return AudioContent(
            source=MediaSourceRef(
                kind=_string(source, "kind", "audio source"),
                value=_string(source, "value", "audio source"),
            ),
            format=fmt,
        )
    if kind == "video":
        _validate_fields(data, _VIDEO_FIELDS, _VIDEO_OPTIONAL_FIELDS, "video part")
        source = _object(data["source"], "video source")
        _exact_fields(source, _SOURCE_FIELDS, "video source")
        raw_format = data.get("format")
        fmt = None
        if raw_format is not None:
            if type(raw_format) is not str or not raw_format.strip():
                raise DomainValidationError("video part.format must be a nonblank string or null")
            fmt = raw_format
        return VideoContent(
            source=MediaSourceRef(
                kind=_string(source, "kind", "video source"),
                value=_string(source, "value", "video source"),
            ),
            format=fmt,
        )
    raise DomainValidationError("unsupported Interaction content kind")


def message_to_dict(message: Message) -> dict[str, object]:
    """Emit an ordered provider-independent v1 mapping with no media I/O."""
    if type(message) is not Message:
        raise DomainValidationError("message_to_dict expects a Message")
    return {
        "schema_version": INTERACTION_SCHEMA_VERSION,
        "object_type": "message",
        "role": message.role.value,
        "content": {"parts": [_part_to_dict(part) for part in message.content.parts]},
    }


def message_from_dict(payload: Mapping[str, object]) -> Message:
    """Decode a strict v1 mapping into immutable Domain Core values.

    Text-to-mapping conversion is the caller's responsibility. Any read-only
    Mapping[str, object], including MappingProxyType, is supported recursively.
    A JSON parser may silently discard duplicate keys, so that boundary needs
    an explicit duplicate-key policy when one is required.
    """
    data = _object(payload, "message")
    _exact_fields(data, _MESSAGE_FIELDS, "message")
    version = data["schema_version"]
    if type(version) is not int or version != INTERACTION_SCHEMA_VERSION:
        raise DomainValidationError("unsupported Interaction schema_version")
    if _string(data, "object_type", "message") != "message":
        raise DomainValidationError("unsupported Interaction object_type")
    role = Role(_string(data, "role", "message"))
    content = _object(data["content"], "content")
    _exact_fields(content, _CONTENT_FIELDS, "content")
    parts = content["parts"]
    if not isinstance(parts, list) or not parts:
        raise DomainValidationError("content.parts must be a non-empty JSON array")
    return Message(role=role, content=Content(parts=tuple(_part_from_dict(part) for part in parts)))
