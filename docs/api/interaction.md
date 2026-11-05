# PyLLMKit Interaction API - text and image content

**Scope:** L2.1/L2.2/L2.3 G2 GO; L2.4 strict Interaction codec integrated and **G3 GO** on `main` SHA `fb4760aa890dceb8c08b16738500b5b28574e60b`, [CI SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077). G4 and technical M2 GO on SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`, [CI SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424); no package publication.

## Public imports

`from pyllmkit.domain.interactions import Role, ContentPart, TextContent, ImageContent, MediaSourceRef, Content, Message`

These same symbols are exposed from `pyllmkit.domain`, which retains all M1 imports.

| Primitive | Public constructor | Validation |
|---|---|---|
| `Role` | `Role.USER` or explicit `Role("user")` | Five canonical values; unknown => `DomainValidationError` |
| `ContentPart` | abstract class | Concrete subclass provides `kind` and M1 `modality` |
| `TextContent` | `TextContent(text: str)` | Exact string required, empty allowed; immutable |
| `Content` | `Content(parts: tuple[ContentPart, ...])` | Nonempty immutable tuple; no coercion, preserves order/duplicates |
| `Message` | `Message(role: Role, content: Content)` | Both required, runtime typed; immutable/value-equal |
| `MediaSourceRef` | `MediaSourceRef(kind: str, value: str)` | `uri`: syntactically valid HTTP(S) URI; `asset`: nonblank opaque ID; original value preserved and repr redacted |
| `ImageContent` | `ImageContent(source: MediaSourceRef)` | Frozen part, strict type, `kind='image'`, `Modality('image')` |

## Acceptance example AC-006

```python
from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(TextContent("Bonjour"),)),
)
assert message.content.parts[0].modality.value == "text"
```

## Acceptance example AC-007

```python
from pyllmkit.domain import Content, ImageContent, MediaSourceRef, Message, Role, TextContent

message = Message(
    Role.USER,
    Content((
        TextContent("Décris cette image : "),
        ImageContent(MediaSourceRef("asset", "image-123")),
        TextContent(" et explique."),
    )),
)
assert tuple(part.kind for part in message.content.parts) == ("text", "image", "text")
```

The API contains no provider SDK, tool execution, inference network call, or persisted conversation. A syntactically valid HTTP(S) URI is **not** a safe-to-fetch URI: adapters must enforce SSRF and content policies before dereferencing. L2.4 adds a strict independent JSON-compatible mapping codec. Role mapping and loss/emulation policy belong to adapters.

## Interaction mapping codec v1 (L2.4)

```python
import json
from pyllmkit.domain import message_to_dict, message_from_dict

raw = json.loads(json.dumps(message_to_dict(message), ensure_ascii=False))
assert message_from_dict(raw) == message
```

See [Interaction JSON Schema v1](../architecture/INTERACTION_JSON_SCHEMA_V1.md). The JSON mapping is a Domain serialization contract, not a provider API payload. It does not fetch media or imply that any URI is trusted.
