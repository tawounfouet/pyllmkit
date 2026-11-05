# ADR-044 - Typed constraint and effective limit reduction

- Date: 2026-11-05
- Status: PROPOSED (P6-G0 review; not yet qualified)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Limit reduction is a pure, conservative calculation over explicitly known limits. For compatible numeric `max_*` bounds use the minimum known upper bound, for `min_*` use the maximum lower bound. Existing `ModelLimits` fields with upper-bound semantics use minimum of known compatible integers. A boolean `False` can restrict `True`; strictly distinguish bool from int (`bool` is a Python `int` subclass). For allowed-value tuples/sets use intersection only when element type and semantic unit agree. Conflicting exact scalar values, incompatible types/units, and unknown constraint names produce a typed conflict / INDETERMINATE diagnostic, not arbitrary coercion.

An absent value remains unknown and must not be set to 0. A known restrictive bound remains useful evidence, but unresolved applicability/type mismatch prevents a claim of fully qualified support. Preserve all source/value evidence in output. A proven empty allowed set means no admissible value, not missing metadata. Detect inconsistent paired min/max bounds; do not silently reorder them. Unknown names require explicit per-name policy before merging.

`EffectiveLimits` and effective capability constraints are derived immutable value objects. Do not mutate `ModelLimits` or M1 `CapabilityConstraint` types, or weaken M3 request validation.

## Verification
P6-AC-028/031/032 plus adversarial tests: mismatched type, bool vs int, negatives, inverted ranges, incompatible units, same value replay, unknown parameter and independent source order.
