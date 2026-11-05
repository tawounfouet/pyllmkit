# PyLLMKit Interaction API - text and image content

**Scope:** L2.1 + L2.2 + L2.3 (G2 GO on 2026-11-05). Candidate `0.1.0a2` API, not a published stable release.

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

The API contains no provider SDK, tool execution, inference network call, or persisted conversation. A syntactically valid HTTP(S) URI is **not** a safe-to-fetch URI: adapters must enforce SSRF and content policies before dereferencing. `message_to_dict`/`message_from_dict` are L2.4 (not offered by these implementations). Role mapping and loss/emulation policy belong to adapters.

**Important:** This is a source-code text/image API, not the versioned Interaction JSON wire contract. JSON round-trips remain pending L2.4.
