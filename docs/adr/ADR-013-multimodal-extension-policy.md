# ADR-013 - Multimodal extension policy for a2

- **Status:** ACCEPTED for Phase 2 design (P2-BOOT, 2026-11-05). Implementation and M2 qualification remain pending.
> **Post-implementation clarification (2026-11-05):** This line records the historical P2-BOOT decision, not the current implementation state. M2's source candidate was subsequently implemented and qualified on [`main@560d3a46`](https://github.com/tawounfouet/pyllmkit/commit/560d3a46c74cecebdf6a55301b2b8ca4e34331d4), [CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) PASS, [M2_GATE_REVIEW](../quality/M2_GATE_REVIEW.md). Package metadata `0.1.0a2` remained unpublished. This note does not revise the 2026-11-05 owner architecture decision.

- **Authorization:** Explicit review and approval by the repository project owner in the PyLLMKit project conversation on 2026-11-05. This is an owner decision, not a GitHub review submission or independent architecture audit.
- **Decision effective date:** 2026-11-05.
- **Context:** The broad domain language includes audio, video, documents and tools, but a2's required acceptance cases are text and image.
- **Sources:** specifications 03, 04, 05, 07 (INT-010/011); Phase 2 plan section 5; ROADMAP 0.1.0a2.

## Decision
1. M2 MUST ship `TextContent`, `ImageContent` and an ordered `Content`. Design the `ContentPart` hierarchy so later modalities can be added without modifying Message semantics.
2. `AudioContent`, `VideoContent` and `DocumentContent` are **deferred implementations** until a precise format/source validation and codec contract are defined. They are explicitly documented extensions, not runtime placeholders.
3. `ToolCallContent` and `ToolResultContent` remain deferred to `0.1.0a4`; their absence does not prevent the symbolic `Role.TOOL`.
4. No `UnknownContent`, transparent dict payload or silent fallback to `TextContent` will masquerade as supported content. Unsupported parts must fail explicitly.
5. An extension's modality is a type descriptor from M1, not a claim of effective Model or Endpoint support. Provider adapter policy is separate.
6. If M2 scope changes to include an extra content kind, first document shape, invariants, versioned codec behavior, negative cases and acceptance evidence, then revise ADR-013.

## Alternatives
- Implement stub audio/video/document classes now: rejected, produces false supported APIs.
- Implement all modalities and transports at once: rejected as premature scope growth.
- Treat all non-text as opaque bytes: rejected, erases domain distinctions and safety policy.

## Consequences
- a2 has genuinely qualified text/image contracts, not fictional broad multimodal support.
- Future additions remain possible through explicit versioning and domain decisions.

## Acceptance Tests
- AC-006 text and AC-007 text/image ordered content pass.
- Unknown part kinds and incomplete multimodal forms are rejected.
- No test or README claims that audio/video/document/tool content is implemented in a2.

## Follow-ups
- L2.4: document supported-vs-planned matrix precisely.
- Future modality increments: audio format rule INT-010 and document distinction INT-011.
