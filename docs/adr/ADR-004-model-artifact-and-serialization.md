# ADR-004 - Model, artifact association and serialization

- **Status:** PROPOSED.
- **Decision:** ModelArtifact has its own ID and references ModelId. Model needs no Artifact to exist. Deployment and Endpoint are outside Phase 1.
- **Decision:** Future codecs use explicit versioned JSON mappings, not blind object dumps.
- **Acceptance:** Model without Artifact; multiple Artifacts per Model; serialization round-trips.
- **Sources:** specs 06, 07.
