# Interaction Domain - Content Primitives (L2.2)

**Status:** implementation candidate on `feature/p2-l22-content-domain`, pending PR CI and integration.
**Decisions:** [ADR-010](../adr/ADR-010-content-polymorphism-and-order.md) and G0.
**Target:** `0.1.0a2`; not a PyPI release.

## Domain objects

- `ContentPart`: abstract, provider-free polymorphic contract exposing `kind: str` and `modality: Modality` (existing M1 type).
- `TextContent(text: str)`: frozen/slotted Value Object; accepts intentional empty string, rejects `None` and all non-strings.
- `Content(parts: tuple[ContentPart, ...])`: frozen/slotted ordered non-empty domain collection. Duplicate parts are retained. Lists, strings and untyped values are rejected rather than coerced.

```python
from pyllmkit.domain import Content, TextContent

content = Content(
    parts=(TextContent("Bonjour"), TextContent(" "), TextContent("PyLLMKit")),
)
assert tuple(part.modality.value for part in content.parts) == (
    "text", "text", "text"
)
```

`kind` discriminates type; `modality` describes content but **does not determine a Model capability or a provider mapping**. The domain performs no network or filesystem I/O, OCR, conversion or implicit flattening.

## Extension boundary

Future `ImageContent` is defined in L2.3, using accepted ADR-011. `Role` and `Message` belong to L2.1. The Interaction JSON schema and its encoding/decoding are L2.4. Unknown future concrete ContentPart types may be modeled as domain parts, but must be **explicitly rejected by the a2 serializer** until separately registered by a reviewed contract.

## Validation

Run `python -m pytest tests/unit/domain/interactions tests/acceptance/test_l22_content_domain.py`, the complete regression suite, Ruff, mypy, packaging and the CI Python 3.11/3.12/3.13 matrix. G1 needs Message/AC-006 as well, so L2.2 alone does not qualify G1.
