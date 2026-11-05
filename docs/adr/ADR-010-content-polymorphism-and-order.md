# ADR-010 - Immutable ContentPart polymorphism and ordered content

- **Status:** PROPOSED FOR REVIEW (P2-BOOT, 2026-11-05). Not yet accepted or merged.
- **Context:** Interleaved text and images need a canonical, ordered and provider-independent representation; a plain `str` or unordered collection is insufficient.
- **Sources:** specifications 03, 05/06, 07 (INT-003/005/008, MOD-003/005); ADR-006; Phase 2 plan.

## Decision
1. `Content` is a frozen, slotted Value Object containing `parts: tuple[ContentPart, ...]` with cardinality 1..*. Validate types and reject empty collections; **do not silently coerce** list/string input.
2. `ContentPart` is the domain polymorphic base contract. Concrete parts are immutable and provide explicit `kind` and `modality` properties; `modality` reuses the existing M1 `Modality` descriptor. The initial recognized kinds are `text` and `image`.
3. `TextContent(text: str)` requires an actual string (never `None`). Empty string `""` is **allowed** as an intentional text value; it still counts as one part. This distinction does not permit a zero-part Content.
4. Order and repeated identical parts carry meaning: never deduplicate, sort, merge adjacent text, OCR an image or normalize whitespace.
5. Each codec-part mapping has an explicit `kind`. Unknown kind/subclass is rejected by the a2 codec, even if future Python subclassing is supported. Future registered types require a reviewed schema evolution strategy.
6. `ContentPart` is a content concept, not a provider SDK object, a capability declaration or a `ToolCall`.

## Alternatives
- `Content = str | list[dict]`: rejected due to loss of domain invariants.
- Tuple of untagged union variants: could work at runtime but loses explicit polymorphic teaching value.
- Permit arbitrary auto-registered subclasses in codec: rejected, makes decoding unsafe and unstable.

## Consequences
- `Content(parts=(TextContent("a"), ImageContent(...), TextContent("b")))` preserves exact order.
- Tests must separately validate immutability, duplicate parts, empty text and empty Content.
- `modality` is descriptive; it never asserts that a Model or Deployment supports the part.

## Acceptance Tests
- `INT-003`: text/image/text retains order and duplicates.
- `INT-005`: zero parts and non-part values rejected.
- `INT-008`: None/non-string text rejected, empty string accepted.
- `MOD-003`: text -> `Modality("text")`, image -> `Modality("image")`.
- `MOD-005`: no OCR, transformation or implicit provider mapping.

## Follow-ups
- L2.2: implement ContentPart, Content, TextContent and role-independent inspections.
- L2.3: implement ImageContent only after ADR-011 is reviewed.
