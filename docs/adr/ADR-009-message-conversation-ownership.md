# ADR-009 - Message value semantics and optional Conversation

- **Status:** PROPOSED FOR REVIEW (P2-BOOT, 2026-11-05). Not yet accepted or merged.
- **Context:** A message is a value representation of one speaker's ordered content. A conversation may group messages but is not a prerequisite for inference.
- **Sources:** specifications 05, 06 (sections 28-30), 07 (INT-001/002/005), 08 (BuildMessage); Phase 2 plan.

## Decision
1. `Message` is a frozen, slotted Value Object with a required canonical `role: Role` and required `content: Content`. The equality contract is by value, without a mandatory `MessageId`.
2. `Content` is a distinct required VO, not an untyped string/list alias; a Message owns exactly one Content.
3. Keep `name`, `metadata`, message timestamps, IDs and provider-native payloads **out of the core a2 minimum** unless a task-specific accepted amendment specifies validated immutable types. Do not add mutable `dict` fields by convenience.
4. `Conversation` is conceptually an optional aggregate (0..* ordered messages), never required to build a Message. **Implementation is deferred from a2** under KISS/YAGNI; the existing specification continues to permit future adoption.
5. The message sequence, if supplied by callers or a future Conversation, is ordered and never automatically sorted, deduplicated or rewritten.

## Alternatives
- Make `Message` an Entity with generated ID: rejected, as identity is unnecessary for representation.
- Require `Conversation` around every `Message`: rejected, introduces persistence/chat coupling.
- Implement Conversation in a2: feasible but not required for AC-006 or AC-007. Deferred.

## Consequences
- `Message(role=Role.USER, content=Content(...))` is independently constructible.
- A3 `InferenceRequest` may accept an ordered sequence of Messages without a Conversation object.
- Message ID and Conversation aggregate are not promised a2 public APIs.

## Acceptance Tests
- Two identical Message values compare equal and cannot mutate.
- Absent or invalid role/content fails deterministically; Content enforces at least one part.
- No Conversation is required to construct a Message or pass AC-006/007.
- Contract documentation explicitly identifies Conversation as deferred.

## Follow-ups
- L2.1 and L2.2: implement Role, Content and Message in dependency order.
- When persistence or collaboration is introduced, decide ConversationId, identity, ownership, and lifecycle in a separate ADR.
