# Model Domain - L1.1

**Status:** Implemented on feature branch, pending PR/CI qualification.
**Sources:** 04, 05, 06, 07 and the Phase 1 implementation plan.

## Vocabulary

- `Model`: logical entity/aggregate identified by `ModelId`, independent of any endpoint.
- `ModelIdentity`: immutable descriptive value; family, version/generation, variant, revision, developer and specialization.
- `ModelFamily`: canonical family label; `ModelVersion` does **not** imply SemVer.
- `ModelArchitecture` and `ModelLimits`: optional; unknown values remain `None` rather than being invented.
- `ModelArtifact`: separate physical Entity with `ModelArtifactId` and a `model_id` reference.
- `ProviderModelRef`: optional provider-specific alias, never the canonical ModelId.

## Example

```python
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelVersion

model = Model(
    id=ModelId("example/family/version"),
    identity=ModelIdentity(
        family=ModelFamily("family"),
        version=ModelVersion("2026-10"),
    ),
)
assert model.architecture is None
assert model.limits is None
```

## Identity and snapshots

`Model` and `ModelArtifact` have Entity identity equality, so two snapshots with the same ID compare equal even with different metadata. They are immutable snapshots; use `with_identity` / `with_limits` for controlled replacement. The objects are intentionally unhashable. Descriptors and typed IDs use value equality.

## Relations

```text
Model (ModelId) -> ModelIdentity
                -> ModelArchitecture? / ModelLimits?
                -> ProviderModelRef* (aliases)

ModelId <- ModelArtifact* (independent Entities)
```

A Model can have zero artifacts and a model may have multiple artifact references through `ModelId`. Neither a Deployment nor an Endpoint is required or implemented in L1.1.

## Schema v1 codec

`model_to_dict`, `model_from_dict`, `artifact_to_dict`, and `artifact_from_dict` expose an explicit versioned JSON-compatible mapping. Missing optional values survive as `null`/`None`. Unknown schema **keys** fail fast to avoid silent data loss; transparent forward-compatible extension storage is left for a subsequent ADR.

## Boundaries

No HTTP, no SDKs, no providers/runtime clients, no registry, no inference. Capabilities and modalities are composed into Model in L1.2; no fake empty defaults are introduced in L1.1.
