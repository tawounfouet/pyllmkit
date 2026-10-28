# ADR-004 - Model, artifact association and serialization

- **Status:** PROPOSED; L1.1 implementation provisionally follows this decision, pending review.
- **Decision:** `ModelArtifact` references a canonical `ModelId`; a `Model` does not have to expose physical artifacts. A `Model` can have none; multiple artifacts can reference the same logical model.
- **Decision:** Explicit `schema_version = 1` for JSON-compatible mappings of Model and Artifact. Unknown optional **values** are preserved as `None`; unknown **schema keys** raise `DomainValidationError` to prevent silent data loss.
- **Trade-off:** Forward-compatible preservation of arbitrary new keys is deferred pending a typed immutable extension model; do not treat this codec as an unversioned wire protocol.
- **Deferred:** Deployment/Endpoint relationships, provider-specific native blobs, registries and artifact store.
- **Acceptance:** independent artifact reference, two artifacts per ModelId, model without artifacts, known fields round-trip, unknown keys explicitly rejected.
- **Sources:** specs 05–07, Phase 1 plan.
