# ADR-003 - UNKNOWN and capability support

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Decision:** Declared support levels are UNSUPPORTED, EMULATED, PARTIAL, NATIVE. An absent declaration remains unknown, not implicitly supported nor unsupported.
- **Acceptance:** unknown stays unknown; partial exposes constraints; emulation is disclosed.
- **Sources:** specs 02, 07.

## Consumer semantics

`supports(id) is False` may mean `UNSUPPORTED` **or UNKNOWN**. Consumers that need this distinction must call `support_of(id).level`. Never treat absent capability as native or unsupported without checking the level.
