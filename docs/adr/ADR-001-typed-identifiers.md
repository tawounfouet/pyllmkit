# ADR-001 - Strongly typed identifiers

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Context:** Model, Artifact, Deployment and Endpoint are separate concepts.
- **Decision:** ModelId and ModelArtifactId will be distinct immutable non-blank string value objects. No implicit coercion or provider-specific format.
- **Rationale:** Type safety, identity and prevention of primitive obsession.
- **Acceptance:** validate blank IDs, same-type equality, cross-type inequality, and serialization round-trips.
- **Sources:** specs 05, 07.

## Canonical identifier policy

No automatic case folding or whitespace stripping: the validated exact string is preserved. Nonblank values are required, allowing existing provider-neutral namespace conventions. Migration/normalization is explicitly deferred to a future ADR.
