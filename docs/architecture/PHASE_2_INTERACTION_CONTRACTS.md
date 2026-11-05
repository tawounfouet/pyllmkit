# Phase 2 - Interaction contracts (P2-BOOT)

**Status:** PROPOSED / REVIEW REQUIRED, 2026-11-05. This describes **future APIs** for `0.1.0a2`, not functionality present on main.
**Baseline:** `main` at `d7f06072d246819fb976c6a456949995ae33562d` (M1-qualified, CI run 40638604245).
**Decision set:** ADR-008..ADR-013. Phase 2 execution plan: `docs/02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md`.

## Architectural intent

PyLLMKit models a provider-independent interaction, not an inference request and not a transport payload. The domain remains stdlib-only, offline and independent of SDKs, deployments, credentials, tools and streaming engines. Explicit role and content semantics belong in the domain. Provider conversions belong in future adapters.

```text
Message (Value Object, frozen, no mandatory ID)
  |- role: Role (system | developer | user | assistant | tool)
  '- content: Content (Value Object, frozen)
        '- parts: tuple[ContentPart, ...]  # one or more, ORDERED
             |- TextContent(text: str)              -> Modality("text")
             '- ImageContent(source: MediaSourceRef) -> Modality("image")
                    |- uri: absolute http(s) URL
                    '- asset: opaque identifier

Conversation (aggregate, optional) -> NOT implemented in a2
InferenceRequest / ToolCall / streaming -> later versions
```

## Proposed public signatures (illustrative, not yet available)

```python
from pyllmkit.domain.interactions import (
    Content, ImageContent, MediaSourceRef, Message, Role, TextContent,
)
from pyllmkit.domain.interactions.serialization import (
    message_from_dict, message_to_dict,
)

message = Message(
    role=Role.USER,
    content=Content(parts=(
        TextContent(text="Regarde"),
        ImageContent(source=MediaSourceRef(kind="asset", value="image-123")),
        TextContent(text="et explique"),
    )),
)
assert message.content.parts[0].modality.value == "text"
assert message.content.parts[1].modality.value == "image"
assert message_from_dict(message_to_dict(message)) == message
```

`Role` is a small canonical string enum. `Message`, `Content`, `TextContent`, `ImageContent` and `MediaSourceRef` are immutable value representations. Enforce strict runtime type checks at construction, rather than relying only on type hints. Use `DomainValidationError` from M1 for invalid structure and codec payloads. The final exact factory/API design will be frozen with implementation tests and reviewed ADRs.

## Content and media rules

- `Content` contains 1..* parts in an immutable tuple. Empty `TextContent("")` is permitted, `TextContent(None)` is not.
- Preserve ordering and duplicates; do not flatten content into a single string or infer roles from the provider.
- `MediaSourceRef(kind="uri", value="https://example.org/image.png")` stores a passive URI; syntactic validation only. Asset refs are opaque nonblank IDs.
- Never fetch, read, decode, OCR, transcribe, upload, infer capability or resolve a provider in value-object constructors or serializers.
- URL validation does not guarantee safety. Network/media access is an adapter concern with independent security controls.
- No guaranteed audio, video, document, inline bytes, data-URI or tool content in `0.1.0a2`.

## Layering and compatibility

```text
pyllmkit.domain.interactions
  -> pyllmkit.domain.modalities   (Modality from M1)
  -> pyllmkit.domain.errors       (DomainValidationError from M1)
  -> Python stdlib
```

Interaction does **not** import domain Model Entities, provider SDKs, HTTP clients, filesystem access, inference/services, adapters or application/facade modules. Preserve existing `pyllmkit.domain` reexports and all M1 subpackage imports; add Interaction reexports only alongside proven implementation. Do not change `pyproject.toml` version in P2-BOOT.

## Independent JSON mapping v1 (design target)

```json
{
  "schema_version": 1,
  "object_type": "message",
  "role": "user",
  "content": {
    "parts": [
      {"kind": "text", "text": "Describe"},
      {"kind": "image", "source": {"kind": "uri", "value": "https://example.org/img.png"}}
    ]
  }
}
```

Only the Interaction codec uses this shape. Strictly reject unknown keys/kinds/schema versions; preserve exact ordered parts. The Model domain `schema_version=1` writer/reader are not modified. JSON examples in this file are **contract proposals**, not output from executable code.

## Traceable acceptance contract

| Requirement | Expected behavior | Implementation gate |
|---|---|---|
| AC-006 | Provider-free text Message | G1 |
| AC-007 | Ordered text/image Message | G2 |
| INT-001/002 | Conversation never required; preserve caller order | G1 |
| INT-003/005 | Ordered nonempty Content | G1/G2 |
| INT-004/006/007 | Valid canonical Role, no lossy provider mapping | G1 |
| INT-008 | `str` text, including explicit empty string | G1 |
| INT-009 | Typed passive image source | G2 |
| INT-010/011 | Documented future audio/document contracts, no pretend implementation | G2 scope |
| MOD-003/005 | Accurate modality, no implicit conversion | G1/G2 |
| ADR-004/005/006 | M1 codec, public API and modality semantics remain intact | G3 |

## Acceptance before promotion

1. Review/adopt or revise ADR-008..013 and record decision authority accurately.
2. Implement Role and ContentPart/TextContent/Content before composing Message.
3. Implement ImageContent and media refs, then Interaction codec and positive/negative tests.
4. Run offline pytest, Ruff, mypy strict, package builds, and examples on Python 3.11/3.12/3.13.
5. Qualify integrated exact-SHA `main` for M2; publication/tagging is an additional separate decision.
