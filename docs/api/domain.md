# PyLLMKit - Phase 1 Python Domain API reference

**Scope:** Proposed in L1.1 / L1.2 stacked PRs. Reference for the 0.1.0a1 *candidate*, not a published stable API.

## Public package boundaries

`pyllmkit.domain.models` exports:

- `ModelId(value: str)` and `ModelArtifactId(value: str)` are different, immutable IDs. Empty or whitespace-only identifiers raise `DomainValidationError`.
- `ModelFamily(value)`, `ModelVersion(value)`, `ModelVariant(value)`, `ModelRevision(value)` describe identity. Versions do not require SemVer.
- `ModelIdentity(family, version=None, variant=None, revision=None, specialization=None, developer=None)`.
- `ModelArchitecture`, `ModelLimits` hold optional information; `None` signifies unknown.
- `Model(id, identity, architecture=None, limits=None, provider_refs=(), capabilities=CapabilitySet(), modalities=ModalitySet())`. Entity equality follows `ModelId`; snapshots are immutable and unhashable.
- `ModelArtifact(id, model_id, format, precision=None, quantization=None, size_bytes=None, source=None, checksum=None, revision=None)`. Separate entity, equality by `ModelArtifactId`.
- `ProviderModelRef(provider_id, model_id, provider_model_name, api_version=None)` is an optional external alias.
- `model_to_dict`, `model_from_dict`, `artifact_to_dict`, `artifact_from_dict` use explicit `schema_version=1`. Unknown schema keys are rejected, not silently discarded.

`pyllmkit.domain.capabilities` exports:

- `CapabilityId(value)` is an extensible lower_snake_case typed ID.
- `SupportLevel`: `UNSUPPORTED`, `EMULATED`, `PARTIAL`, `NATIVE`. `None` is unknown.
- `CapabilityConstraint(name, value)` validates a typed constraint.
- `CapabilitySupport(level=None, constraints=(), notes=None)` models declared support; `PARTIAL` requires constraints or notes.
- `Capability(id, support=CapabilitySupport())`.
- `CapabilitySet(items=())`: `get`, `contains`, `supports`, `support_of`, `union`, `intersection`, `difference`. Conflicting declarations raise `DomainValidationError`; this is **not** an effective-capabilities resolver.

`pyllmkit.domain.modalities` exports:

- `Modality(value)`: typed lower_snake_case input/output content category.
- `ModalitySet(input_modalities=None, output_modalities=None)`: directional modality collections. `None` denotes unknown; an empty `frozenset()` denotes explicitly empty. `accepts_input` and `can_output` return `bool | None`.

`pyllmkit.domain.errors` exports `PyLLMKitError`, `DomainValidationError`.

## DDD and semantic contracts

- `Model` is an entity/aggregate root with stable logical identity.
- `ModelArtifact` is an independent physical entity, referenced by `ModelId`.
- `Capability` is about **what can be done**; `Modality` is about **what data kind is involved**.
- Unknown is not automatically unsupported and is never silently native.
- `Usage`, `InferenceRun`, `Deployment`, `Endpoint` are separate later bounded contexts, not implemented in P1.
- All types above can be constructed without network, secrets or provider SDKs.

## Examples

Run `python examples/01_define_model.py`, `python examples/02_define_artifacts.py`, `python examples/03_define_capabilities.py` after installing this source checkout.

## Limitations

The domain API surface and codec compatibility policy are **pre-release** and subject to ADR approval. The static import guard and socket-blocked pytest fixture reduce risk but do not constitute an exhaustive security review.
