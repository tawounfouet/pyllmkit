# ADR-001 - Strongly typed identifiers

- **Status:** PROPOSED.
- **Context:** Model, Artifact, Deployment and Endpoint are separate concepts.
- **Decision:** ModelId and ModelArtifactId will be distinct immutable non-blank string value objects. No implicit coercion or provider-specific format.
- **Rationale:** Type safety, identity and prevention of primitive obsession.
- **Acceptance:** validate blank IDs, same-type equality, cross-type inequality, and serialization round-trips.
- **Sources:** specs 05, 07.
