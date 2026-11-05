# ADR-010 - Immutable ContentPart polymorphism and ordered content

- **Status:** ACCEPTED for Phase 2 design (P2-BOOT, 2026-11-05). Implementation and M2 qualification remain pending.
> **Post-implementation clarification (2026-11-05):** This line records the historical P2-BOOT decision, not the current implementation state. M2's source candidate was subsequently implemented and qualified on [`main@560d3a46`](https://github.com/tawounfouet/pyllmkit/commit/560d3a46c74cecebdf6a55301b2b8ca4e34331d4), [CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) PASS, [M2_GATE_REVIEW](../quality/M2_GATE_REVIEW.md). Package metadata `0.1.0a2` remained unpublished. This note does not revise the 2026-11-05 owner architecture decision.

- **Authorization:** Explicit review and approval by the repository project owner in the PyLLMKit project conversation on 2026-11-05. This is an owner decision, not a GitHub review submission or independent architecture audit.
- **Decision effective date:** 2026-11-05.
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
