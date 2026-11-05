# ADR-042 - Typed query and deterministic catalog search

- Date: 2026-11-05
- Status: PROPOSED (P6-G0 review; not yet qualified)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
`ModelQuery` and `DeploymentQuery` are frozen typed value objects. Model filters: canonical model ID, model family, documented developer (only when known), explicit provider alias, required capability IDs, input/output modalities, known minimum context window. Deployment filters: model ID, optional provider ID, region, runtime, declared status, required capabilities/modalities. Apply provided criteria using logical AND; no implicit fuzzy match, alias rewriting or ranking.

A missing metadata value, empty declaration, or UNKNOWN support **never satisfies a positive strict requirement**. Directional input vs output modality filters remain separate. A known limit must meet the threshold; `None` is unknown, not unbounded or zero. Capability queries need an explicit `native_only` or `usable` policy. `usable` can include PARTIAL/EMULATED only when explicitly requested; `UNSUPPORTED` and UNKNOWN never pass. Provider alias filtering reads declared `ProviderModelRef` and does not redefine ModelId. For deployment effective search, use L6.4 resolver rather than intrinsic model support alone.

All results sorted lexically by `id.value`, independent of insertion sequence or source ordering. No pagination until a measured use case requires it; if later added, sorting remains fixed and pagination must be stable. Queries do not mutate catalog or make network calls.

## Alternatives
Rejected: choosing "best model" by incidental insertion order, returning unknown records as strict matches, conflating intrinsic and effective support.

## Verification
P6-AC-017..024, matching and exclusion tests for all filters, repeated different insertion order, invalid types, side-effect-free query checks.
