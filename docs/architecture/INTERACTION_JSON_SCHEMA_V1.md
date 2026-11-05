# Interaction JSON v1 - PyLLMKit Domain Contract

**Status:** L2.4 implementation candidate; qualification requires PR and integrated main CI.
**Decision:** ADR-012 ACCEPTED; independent from the Model Domain schema.
**Scope:** 0.1.0a2 candidate, not a published external wire standard.

## Public API

```python
from pyllmkit.domain.interactions.serialization import (
    INTERACTION_SCHEMA_VERSION, message_to_dict, message_from_dict,
)
```

`message_to_dict(message: Message) -> dict[str, object]` emits a JSON-compatible mapping.
`message_from_dict(payload: Mapping[str, object]) -> Message` strictly recreates immutable Domain Core values. Text parsing is performed by the caller using standard `json.dumps` / `json.loads`.

## Canonical v1 payload

```json
{
  "schema_version": 1,
  "object_type": "message",
  "role": "user",
  "content": {
    "parts": [
      {"kind": "text", "text": "Regarde"},
      {"kind": "image", "source": {"kind": "asset", "value": "image-123"}},
      {"kind": "text", "text": "Explique"}
    ]
  }
}
```

Top-level keys: exactly `schema_version`, `object_type`, `role`, `content`.
`content`: exactly `parts`, a nonempty JSON array. Text: `kind` and `text`. Image: `kind` and `source`. Source: exactly `kind` and `value`, using passive `uri` or `asset` references validated by ADR-011.

## Strictness

- Schema version must be exact JSON integer 1, not boolean, string or floating point.
- Object type is exactly `message`; role is one of five canonical Role values.
- Reject unknown/missing keys at all levels, unsupported part kinds, nulls and wrong types with `DomainValidationError`.
- Preserve ordering, duplicates, text including deliberate empty strings, exact Unicode/whitespace, and source kind/value through dict -> JSON -> dict -> Message.
- Unknown future `ContentPart` subclasses are not silently serialized. Evolution requires a reviewed schema decision.
- No provider-native payloads or automatic role coercions.
- The exact full URI is included in emitted mappings to allow lossless round-trip. Error messages deliberately avoid echoing URI values. Do not log arbitrary mapping data without explicit redaction.
- URI syntax checking is not URL safety or SSRF policy. No network or asset resolver exists in the codec.
- The mapping decoder does not parse JSON text. The standard JSON decoder may discard duplicate keys. Callers that need duplicate-key rejection must enforce it at their JSON parser or transport boundary.
- JSON data size limits and media fetching security belong in future application and adapter boundaries.

## Compatibility

- Model Domain codec and `SCHEMA_VERSION` v1 remain unchanged.
- This codec has its own independent `INTERACTION_SCHEMA_VERSION` constant, even though both namespaces initially use integer 1.
- No `Conversation`, Message IDs/timestamps/metadata, audio/video/document content, ToolCall/ToolResult or provider-native fields are supported in Interaction v1.
- This is a source-code candidate, not a published library or external provider wire protocol.

## Evidence targets

- `tests/serialization/test_interaction_codec.py`: schema, errors, Unicode, order, media refs.
- `tests/serialization/test_interaction_codec_extension.py`: unknown subtype refusal.
- `tests/acceptance/test_ac_006_007_roundtrip.py`: text and mixed multimodal round trips.
- `examples/07_round_trip_interaction.py`: exercised by the CI.
- GitHub Actions: Python 3.11-3.13, mypy strict, Ruff, offline suite, wheel/sdist smoke.
