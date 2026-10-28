# ADR-004 - Model, artifact association and serialization

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Decision:** `ModelArtifact` references a canonical `ModelId`; a `Model` does not have to expose physical artifacts. A `Model` can have none; multiple artifacts can reference the same logical model.
- **Decision:** Explicit `schema_version = 1` for JSON-compatible mappings of Model and Artifact. Unknown optional **values** are preserved as `None`; unknown **schema keys** raise `DomainValidationError` to prevent silent data loss.
- **Trade-off:** Forward-compatible preservation of arbitrary new keys is deferred pending a typed immutable extension model; do not treat this codec as an unversioned wire protocol.
- **Deferred:** Deployment/Endpoint relationships, provider-specific native blobs, registries and artifact store.
- **Acceptance:** independent artifact reference, two artifacts per ModelId, model without artifacts, known fields round-trip, unknown keys explicitly rejected.
- **Sources:** specs 05–07, Phase 1 plan.

## Alpha freeze - Schema version 1

The final alpha `schema_version=1` writer is frozen with optional `capabilities` and `modalities` fields. The reader accepts earlier development-time v1 snapshots without them. The old strict development-time reader does not necessarily accept the current emitted v1 format: this is **backward-read-only compatibility**, not bidirectional compatibility. Do not add fields to v1 output without an explicit versioning decision; future incompatible changes use schema v2 plus migrations. No schema v1 was previously published externally.
