# Interaction Domain - MediaSourceRef & ImageContent (L2.3)

**Status:** L2.3 implementation candidate, pending PR CI and integration into main.
**Scope:** `0.1.0a2` candidate, not published.
**Decisions:** [ADR-010](../adr/ADR-010-content-polymorphism-and-order.md), [ADR-011](../adr/ADR-011-media-source-safety.md) and [ADR-013](../adr/ADR-013-multimodal-extension-policy.md).
**Acceptance:** AC-007 (ordered text-image-text Message).

## Public types

```python
from pyllmkit.domain import Content, ImageContent, MediaSourceRef, Message, Role, TextContent

message = Message(
    role=Role.USER,
    content=Content(parts=(
        TextContent("Regarde : "),
        ImageContent(source=MediaSourceRef("asset", "image-123")),
        TextContent(" Décris-la."),
    )),
)
assert [part.modality.value for part in message.content.parts] == [
    "text", "image", "text"
]
```

`MediaSourceRef(kind: str, value: str)` is a **frozen, slotted Value Object** with two source kinds:

- `kind="asset"`: a nonblank opaque string ID; no storage backend, file-system semantics or resolver.
- `kind="uri"`: absolute HTTP(S) URI with syntactically valid host, optional port, path/query/fragment. A syntactically valid URI **does not mean it is trusted, reachable or safe to fetch**. `localhost` and private IPs may be syntactically valid but are NOT pre-approved for network access.

The domain rejects unsupported schemes (`file:`, `data:`, FTP, local paths), missing hosts, malformed host/port and inline bytes. Values are preserved exactly, without downloading or decoding. `repr(MediaSourceRef)` redacts the entire value to avoid inadvertent disclosure of embedded credentials or query secrets. Error messages do not include submitted URL content.

`ImageContent(source: MediaSourceRef)` is an immutable `ContentPart` with `kind="image"` and `modality=Modality("image")`. This describes input data only; it **does not** assert provider vision capability, OCR, image generation, or source trust.

### Layer responsibility

```text
Domain Core: typed passive reference, syntactic validation and content ordering
Future adapter: URL allowlist, SSRF defenses, DNS/IP policy, redirects,
                authentication, payload size limits, MIME and content validation
```

There is no network call, file read, OCR, or image transformation in the Domain Core. Security checks needed before dereferencing a URI belong to future adapters.

## Not included yet

- The independent Interaction JSON codec (`message_to_dict`, `message_from_dict`) is **L2.4**. Source round-trip tests through JSON are future work, not evidence for L2.3.
- Audio, video, document and tool-call content are deferred under ADR-013.
- Model provider adapters, inference requests and external media handling are deferred to later phases.
- Completion of this code alone is not **M2 GO**, a Git tag, GitHub Release or PyPI publication.

## Validation

Run `pytest tests/unit/domain/interactions/test_media_source_ref.py tests/unit/domain/interactions/test_image_content.py tests/acceptance/test_ac_007_multimodal_message.py`, full regression tests, Ruff, mypy strict, offline examples and Python 3.11/3.12/3.13 CI.
