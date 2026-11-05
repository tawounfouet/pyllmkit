# ADR-047 - Explicit, atomic catalog merge policy

- Date: 2026-11-05
- Status: ACCEPTED for P6 offline technical architecture by owner-delegated authorization, 2026-11-05 (independent GitHub review absent)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Merging `DiscoveryResult` is **opt-in**: first compute a dry-run `MergePreview` with adds, identical no-ops, invalid references and typed `RegistryConflict` records (entity type, canonical ID, conflicting fields and provenance). Default `MergePolicy` is `FAIL_ON_CONFLICT`; any unresolved discrepancy rejects the whole batch. Never silently prefer newer timestamps, provider order or last writer.

The coordinated InMemory merge validates all Provider, Model and Deployment changes and references against a *candidate copy* of the three registries, using provider/model/deployment dependency order. Commit all three together by swapping the candidate snapshot **only after full validation**, otherwise leave the original state unchanged. Single-process snapshot atomicity is the only claimed guarantee; not distributed transactions or cross-process isolation. Idempotent repeat of the same batch is a no-op.

Optional explicit per-conflict resolution (chosen source or chosen revision) requires a recorded policy, stable tie-breaking, and a test for replay determinism. A policy refusing conflict is the required MVP; silent override is never permitted. Conflicts do not emit fake success events.

## Verification
P6-AC-045..048: reject conflicting model snapshot despite ID equality, rollback of partial candidate additions, referential violations, replay, inverse import order under the same explicit policy and dry-run equivalence.
