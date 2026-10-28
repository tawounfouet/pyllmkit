# ADR-006 - Capability & modality declaration semantics

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Context:** The domain needs extensible capability/modalities, explicit support and proper treatment of unknown facts. Specs 04/05/07; L1.2 backlog T01–T09.
- **Decision:** `CapabilityId` and `Modality` are string-backed lower_snake_case value objects; `SupportLevel` is the explicit 4-level enum. Absent support is `None`, not a guessed level. A `PARTIAL` declaration includes constraints or notes.
- **Decision:** `CapabilitySet` stores immutable unique declarations; `supports()` means explicit available support; unknown maps to false without losing `support_of(...).level = None`.
- **Decision:** Union/intersection of declarations accept equal overlapping entries only; conflicting values raise rather than silently resolving. The effective restrictive resolver is deferred until the Serving model is implemented.
- **Decision:** `ModalitySet` separates input from output; `None` is unknown, empty frozenset is explicitly empty. No implicit modality conversion.
- **Decision:** Model composes both sets with unknown-by-default declarations. L1.1 schema v1 may add optional fields with backward-compatible decoding; new schema keys remain strictly checked.
- **Trade-offs:** No ready-to-use effective capability negotiation and no arbitrary constraints merge; intentionally limited to foundational domain vocabulary.
- **Acceptance:** known/unknown/unsupported distinction, partial and emulated annotations, collection behavior, directional modalities, JSON roundtrip, no provider imports.

## Explicit deferral

`CapabilitySet.union/intersection` enforce *identical* overlapping declarations. They are not effective capability negotiations or automatic restrictive set merges across provider, deployment and endpoint. An `EffectiveCapabilitySet` / dedicated resolver will be designed in a future phase.
