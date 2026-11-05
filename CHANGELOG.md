# Changelog

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
- This is a **repository candidate only**: no Git tag, GitHub Release or PyPI publication, and M2 GO remains subject to integrated main qualification.

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
