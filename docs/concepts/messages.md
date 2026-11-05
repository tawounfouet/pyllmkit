# Interaction Domain - Message and Roles (L2.1)

**Status:** implementation candidate pending L2.1 PR integration and exact-SHA main CI.
**Decisions:** [ADR-008](../adr/ADR-008-role-taxonomy.md), [ADR-009](../adr/ADR-009-message-conversation-ownership.md), [ADR-010](../adr/ADR-010-content-polymorphism-and-order.md).
**Acceptance:** AC-006 - a provider-agnostic text Message.

## Five semantic roles

`Role` is a string-valued enum with exactly `SYSTEM`, `DEVELOPER`, `USER`, `ASSISTANT`, `TOOL`. Their serialized *values*, for future codecs, are `system`, `developer`, `user`, `assistant`, `tool`.

The Domain Core rejects unknown roles, and Message does not implicitly coerce a string to a Role. An explicit `Role("user")` can parse a known value; `Message(role="user", ...)` is invalid. `Role.TOOL` does not imply tool execution or tool-result correlation.

## Message Value Object

```python
from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(TextContent("Bonjour"), TextContent(" PyLLMKit"))),
)
assert message.content.parts[0].text == "Bonjour"
```

`Message` is a frozen, slotted, value-equal object. It owns exactly one `Content`; its `parts` collection is a tuple and retains order and duplicates. No message ID, name, mutable metadata, timestamp, provider payload, or Conversation object is required or injected. An ordered tuple of Messages is valid by itself.

## Boundaries and deferred work

- No provider SDKs, network, secrets, mapping, I/O, or capability inference in constructors.
- `Conversation` remains an optional *concept* whose actual aggregate implementation is deferred.
- Image sources / ImageContent are L2.3, and the versioned Interaction JSON codec is L2.4.
- `InferenceRequest` is a3; tool calling is a4.
- M1 Model codec v1 and public imports remain unchanged.
- A green AC-006 and L2.2 does **not** qualify M2, which also requires multimodal and codec gates.

## Verification

`python -m pytest tests/unit/domain/interactions tests/acceptance/test_ac_006_text_message.py`, the full CI Python matrix, offline examples and packaging.
