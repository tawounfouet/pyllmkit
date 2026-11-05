# ADR-043 - Conservative effective capability semantics

- Date: 2026-11-05
- Status: ACCEPTED for P6 offline technical architecture by owner-delegated authorization, 2026-11-05 (independent GitHub review absent)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Implement pure `CapabilityResolver` and derived immutable `EffectiveCapabilityReport` / `EffectiveCapabilitySet` over applicable Model, Deployment and Provider snapshots (future Endpoint only once modeled). Each capability has per-layer evidence, final level, constraints and explicit reason codes. A missing declaration at an **applicable** layer is UNKNOWN (`None` in existing `CapabilitySupport`), not NATIVE. `NOT_APPLICABLE` is **a separate applicability fact**, only when that layer is structurally absent (e.g. proven local deployment without provider); never infer it from missing metadata.

A known UNSUPPORTED declaration vetoes all layers, including UNKNOWN. Otherwise, any UNKNOWN makes effective support UNKNOWN. All applicable NATIVE produces NATIVE. PARTIAL with other NATIVE produces PARTIAL; EMULATED with other NATIVE produces EMULATED. A mixture of PARTIAL and EMULATED produces PARTIAL **plus an explicit emulated marker and per-layer evidence**; these two levels are not treated as a natural total ordering. Zero applicable declarations cannot fabricate NATIVE. No final support is independently persisted.

No change to `CapabilitySet.intersection()` (M1 collection operation), `SupportLevel` enum, `CapabilitySupport`, or existing `GenerationSupportSnapshot` and `CompatibilityReport` (M3 parameter compatibility). The resolver can consume the former and hand the latter a compatible projection later; they are not interchangeable.

## Alternatives
Rejected: `min(SupportLevel)`, missing provider equals native, overwriting intrinsic model capability with a deployment declaration, rewriting M3 compatibility.

## Verification
P6-AC-025..030 and 032, including all pairwise known/unknown/veto cases, unsupported + unknown, local provider inapplicability, partial+emulated evidence, purity and deterministic order.
