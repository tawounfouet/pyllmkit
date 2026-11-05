# PyLLMKit Interaction API - text foundation

**Scope:** L2.1 + L2.2. Candidate `0.1.0a2` API, not yet a published stable release.

## Public imports

`from pyllmkit.domain.interactions import Role, ContentPart, TextContent, Content, Message`

These same symbols are exposed from `pyllmkit.domain`, which retains all M1 imports.

| Primitive | Public constructor | Validation |
|---|---|---|
| `Role` | `Role.USER` or explicit `Role("user")` | Five canonical values; unknown => `DomainValidationError` |
| `ContentPart` | abstract class | Concrete subclass provides `kind` and M1 `modality` |
| `TextContent` | `TextContent(text: str)` | Exact string required, empty allowed; immutable |
| `Content` | `Content(parts: tuple[ContentPart, ...])` | Nonempty immutable tuple; no coercion, preserves order/duplicates |
| `Message` | `Message(role: Role, content: Content)` | Both required, runtime typed; immutable/value-equal |

## Acceptance example AC-006

```python
from pyllmkit.domain import Content, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(TextContent("Bonjour"),)),
)
assert message.content.parts[0].modality.value == "text"
```

The API contains no provider SDK, tool execution, inference network call, or persisted conversation. `ImageContent` is L2.3; `message_to_dict`/`message_from_dict` are L2.4 (not offered by these implementations). Role mapping and loss/emulation policy belong to adapters.

**Important:** This is a source-code text API, not the versioned Interaction JSON wire contract.
