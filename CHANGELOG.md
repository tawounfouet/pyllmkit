# Changelog

## [Unreleased development] - L3.5 Integration & Packaging (G5 candidate, not released)

### Integrated documentation and regression quality (pending G5 qualification)
- Harmonized README current gate status and runnable offline Inference Request/Response/Run JSON v1 walkthrough, P3-AC-030.
- Added consolidated `docs/api/inference.md`, Request/Response/Run conceptual guides, actual architecture contract diagram and JSON v1 schema guide.
- Added `PHASE_3_TRACEABILITY.md` linking all 30 P3 acceptance cases to tests, ADRs, PRs and qualified main CI.
- Added public root/subpackage import tests, release-metadata/license/typing tests, docs integrity checks and `examples/12_full_inference_walkthrough.py` smoke-tested from installed wheel/sdist.
- Resolved M2 PIR2-01/02/03 separately via [PR #31](https://github.com/tawounfouet/pyllmkit/pull/31), [main 2ec317de](https://github.com/tawounfouet/pyllmkit/commit/2ec317de98bd9d0897fe1e48801a9727e4f7ced6) and [CI #42057132634](https://github.com/tawounfouet/pyllmkit/actions/runs/42057132634) (789 tests, 95% coverage). Issue #20 completed.

**G5 and M3 NOT YET QUALIFIED at this changelog revision.** Main protection issue #22 remains open. The repository still declares `0.1.0a2` and nothing has been tagged or published.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G4 only, not released)

### Added (L3.4 - Inference JSON Codec & Quality)
- Strict independent INFERENCE_SCHEMA_VERSION=1: complete JSON-compatible dictionaries for InferenceRequest, InferenceResponse and all six InferenceRun snapshots.
- Exact required nullable keys; nested Interaction JSON v1 messages; canonical UTC timestamps; typed config, reason, usage and Run invariant validation.
- Negative schema and sanitized-error tests, P3-AC-021..028, six-state round-trips, offline example 11, clean wheel/sdist codec smoke tests and API guide.
- G4 qualification on [PR #29](https://github.com/tawounfouet/pyllmkit/pull/29), [main d72b1ce](https://github.com/tawounfouet/pyllmkit/commit/d72b1ce82a4a34c62888ad48b50bcf07537f83d1), [CI #42053906726](https://github.com/tawounfouet/pyllmkit/actions/runs/42053906726): **779 tests / 95 % coverage**, Python 3.11/3.12/3.13. [Gate report](docs/quality/P3_G4_GATE_REVIEW.md).

**Not implemented:** provider or network inference, streaming, HTTP parser duplicate-key policy, production release. Metadata remains 0.1.0a2.


## [Unreleased development] - 0.1.0a3 Inference Primitives (G3 only, not released)

### Added (L3.3 - Run Lifecycle Ready)
- Immutable `InferenceRun` Aggregate Root with six states, pure transitions, injected timezone-aware timestamps, terminal `finished_at`, RunId identity equality and strict snapshot invariants.
- `InferenceFailure` normalized snake_case codes and optional cancellation code, without native provider payload; response correlation checked during completion.
- P3-AC-014..020 and P3-AC-029, negative tests and reconstructed snapshot validation, offline example 10, public API docs and wheel/sdist smoke.
- G3 technical qualification: [PR #27](https://github.com/tawounfouet/pyllmkit/pull/27), [main 361791ff](https://github.com/tawounfouet/pyllmkit/commit/361791ff546612e10b407874c54014b1c0e1ce86), [CI #42044787119](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119), 679 tests, 94 % coverage and three Python versions. [G3 report](docs/quality/P3_G3_GATE_REVIEW.md).

**Still excluded:** real streaming, network/provider invocation, persistence, retry engine, event bus and Inference JSON v1 codec (L3.4). No version bump, tag or release.


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
