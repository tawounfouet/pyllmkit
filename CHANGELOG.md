# Changelog

## [Unreleased development] - 0.1.0a3 Inference Primitives (G2 only, not released)

### Added (L3.2 - Response Ready)
- Immutable InferenceRunId, TextOutput with explicit empty text, InferenceOutput conceptual alias, normalized FinishReasonCode and FinishReason with optional native provenance.
- Usage with five optional exact nonnegative counters, no inferred total or pricing, plus immutable InferenceResponse correlated by explicit RunId.
- Unit/negative and acceptance tests P3-AC-008..013, offline example 09, public API docs, updated architecture fitness checks and wheel/sdist smoke tests.
- G2 qualification based on [PR #25](https://github.com/tawounfouet/pyllmkit/pull/25), integrated main SHA 783aa4381dc05a4b9bc431faab282f2bbe37d38d, [CI #42039312011 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011): 545 tests, 94% coverage, three Python versions. [G2 gate report](docs/quality/P3_G2_GATE_REVIEW.md).

**Not yet in a3:** Run lifecycle, Inference JSON codec v1, tool execution, provider adapters, real streaming, HTTP, release or PyPI. Metadata stays 0.1.0a2.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G1 only, not released)

### Added (L3.1 - Request Ready)
- Provider-free typed ModelTarget, DeploymentTarget, EndpointTarget and opaque Serving IDs.
- Immutable InferenceRequest for ordered Phase 2 Message values; strict GenerationConfig without provider-specific defaults.
- Explicit pure support evaluation from caller-supplied GenerationSupportSnapshot. Unknown remains unknown, known UNSUPPORTED is rejected (ADR-021 option A, P3-AC-007).
- Domain/root imports, offline acceptance tests P3-AC-001..007, Python 3.11-3.13 CI examples and clean wheel/sdist API smoke tests.
- G1 technical qualification based on main SHA f1ef04b8ff1bb52a1ee17defa0ec8b20f84ac9d3 and CI #42036557565: 432 tests, 93% coverage (Python 3.11). [G1 gate](docs/quality/P3_G1_GATE_REVIEW.md).

**Not implemented yet:** Response, Run, Inference JSON v1, tools, structured output, streaming, provider adapters and external invocation. Metadata stays 0.1.0a2 and no release is authorized.


All notable changes to PyLLMKit are tracked here. The metadata version does not imply external publication.

## [Unreleased] - 0.1.0a2 candidate

### Added (Phase 2)
- Canonical Role and immutable Message Value Object for provider-free text interactions (AC-006).
- Typed ordered ContentPart / TextContent / Content, with strict non-empty collections.
- Passive MediaSourceRef and ImageContent, preserving text/image/text ordering (AC-007).
- Independent Interaction JSON mapping schema v1 (ADR-012), with strict parsing, explicit version, and reversible text/image content including URI and asset references.
- G0/G1/G2 evidence, ADR-008 through ADR-013, L2.4 negative tests and offline examples.
- Python 3.11/3.12/3.13 CI checks, wheel/sdist Interaction API smoke tests.

### Compatibility and scope
- M1 Model and Artifact JSON codecs remain independent and unchanged.
- JSON input is a mapping; duplicate-key checks on raw JSON text are a caller/parser responsibility.
- URI validation is syntactic, not a security policy for fetching media.
- No provider adapters, Conversation aggregate, audio/video/document or tool execution.
- This is a **repository candidate only**: no Git tag, GitHub Release or PyPI publication. L2.4 G3 and integrated G4/M2 technical GO are qualified on `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`. Publication remains a distinct, unapproved action.

## [Unreleased] - 0.1.0a1 candidate

### Added
- Provider-independent Model, ModelId, ModelIdentity, ModelFamily, ModelVersion, ModelVariant, ModelRevision and ModelArchitecture/ModelLimits value objects.
- Independent ModelArtifact entity and provider alias descriptor; identity-based equality and immutable snapshots.
- Capability, CapabilitySet, CapabilitySupport, typed constraints and explicit NATIVE/PARTIAL/EMULATED/UNSUPPORTED/UNKNOWN semantics.
- Input/output ModalitySet and distinct Modality descriptions.
- JSON-compatible Model/Artifact schema-v1 codecs with strict unknown-key rejection.
- Explicit `pyllmkit.domain` public imports and equivalent subpackage imports.
- Offline and negative architecture tests, acceptance traceability, branch coverage in CI.
- Python 3.11/3.12/3.13 lint/type/test/build matrix; clean wheel and sdist smoke installs.
- ADR-001 through ADR-007, MIT license and M1 qualification dossier.

### Constraints
- Effective provider/deployment capability resolution is not implemented.
- No registry, inference engine, provider adapters, streaming or tool execution.
- Schema-v1 read compatibility is one-way for older development snapshots.
- No GitHub release, git tag or PyPI publication as part of milestone qualification.
