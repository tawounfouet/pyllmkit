# Phase 6 - Registry & Discovery architecture (P6-G0)

- Date: 2026-11-05
- Status: PROPOSED; pending owner/design review, merge and exact-main CI
- Baseline: `19cc1c9e1d5598711890ddc3e14f1da94c79ce70` (`0.1.0a2`)
- Target milestone: M6; indicative distribution version `0.1.0b2`, **not authorized**

## Purpose and bounded context
P6 describes models, providers and deployments, searches a catalog, conservatively derives effective support, resolves a unique deployment and previews/merges **offline** discovery. No inference invocation occurs. Provider metadata registry does not store executable adapter factories. Prior phase-numbering divergence is settled *for the roadmap only* by ADR-039: P6 is Registry & Discovery; executable provider adapters are deferred.

## Logical dataflow

```text
Caller / notebook / future façade
  | (read/query commands)
  v
Application registry services -> ModelRegistryPort + DeploymentRegistryPort + ProviderCatalogPort
  |                              |                |                 |
  |                           InMemoryModel   InMemoryDeployment  InMemoryProvider
  |                                           (offline adapters)
  +--> ModelQuery / DeploymentQuery -> deterministic sorted catalog result
  +--> CapabilityResolver (pure) --> EffectiveCapabilityReport + evidence
  +--> DeploymentResolver (read-only) --> one eligible Deployment / typed failure

Static/fixture DiscoverySourcePort --> DiscoveryResult + MetadataSource
  --> MergePreview (read-only) --> MergePolicy (explicit)
  --> coordinated candidate snapshot --> atomic in-memory commit OR full rejection

Lower-level dependencies: domain.models, domain.capabilities, domain.modalities,
                          domain.inference.targets (all reused unchanged)
NOT in P6: SDKs, HTTP, healthchecks, keys, AdapterRegistry, actual endpoints,
           LLM invocation, routing/retries, agent orchestration, external storage
```

## Package design (additive)

```text
src/pyllmkit/domain/providers/       ProviderId, InferenceProvider
src/pyllmkit/domain/deployments/     Deployment, DeploymentStatus
src/pyllmkit/domain/registry/        ModelQuery, DeploymentQuery, Evidence,
                                      EffectiveCapabilityReport, EffectiveLimits,
                                      DiscoveryResult, MetadataSource, typed errors
src/pyllmkit/protocols/registry.py   ModelRegistryPort, DeploymentRegistryPort,
                                      ProviderCatalogPort, DiscoverySourcePort
src/pyllmkit/adapters/registry/     InMemory*; optional StaticCatalog
src/pyllmkit/application/registry/  Catalog service, DeploymentResolver,
                                      preview/apply coordinated merge
```

Domain must have no imports from application, adapters, SDKs or I/O code. Existing `domain.inference` and `domain.streaming` must remain unchanged unless a later ADR explicitly requires a compatible additive adapter. `Model.__eq__` is identity-only: collision checking MUST use a complete declarative snapshot comparison.

## Aggregate/relationship contract

| Subject | Canonical identity | Required references | Rule |
|---|---|---|---|
| Model (existing) | ModelId | none | One model can have 0..n deployments |
| InferenceProvider | new ProviderId | none | Descriptive metadata; never executable SDK |
| Deployment | existing DeploymentId | ModelId; ProviderId optional | Local deployments may have no provider |
| Registry | typed port | canonical ID | No creation on read; no cascades |
| DiscoveryResult | source + observation | candidate IDs | No registry mutation until approved merge |

Three registries are distinct even if all are backed by in-memory maps. All query output is immutable and sorted by ID. Registration same ID and same complete snapshot is idempotent; conflicting metadata is an error, not update. Deletion of referenced Model/Provider is refused.

## Capabilities and limits

| Evidence from applicable layers | Derived result | Explanation |
|---|---|---|
| Every layer NATIVE | NATIVE | Complete known support |
| Any UNSUPPORTED | UNSUPPORTED | Explicit veto |
| Any UNKNOWN without veto | UNKNOWN / None | Non-routable by default |
| PARTIAL plus NATIVE | PARTIAL | Preserve constraints |
| EMULATED plus NATIVE | EMULATED | Declare emulation |
| PARTIAL plus EMULATED | PARTIAL + emulated flag | Preserve both source facts |
| Proven structurally absent provider | NOT_APPLICABLE for that layer | Not confused with unknown |

Effective support and limits are derived, not persisted as truth. Numeric maximums take the lowest compatible declared bound; boolean restrictions and typed allowed-value intersections are conservative. Unknown/mismatched units or types produce conflict evidence. `CapabilitySet.intersection()` remains only a collection operator, not a domain resolver.

## Use cases and failure semantics

1. Register/get/list/find/remove models, providers and deployments, with strict identity and referential checks.
2. Typed AND queries; all positive strict criteria require known confirming evidence; deterministic sorting.
3. Resolve a ModelTarget to **exactly one** deployment satisfying hard constraints and declared status; otherwise typed NOT_FOUND/AMBIGUOUS/UNSUPPORTED/UNKNOWN, never a hidden first-match or fallback.
4. Discovery source produces normalized offline proposals, explicit UTC timestamp and provenance; preview before any mutation.
5. Merge in one coordinated in-memory copy-on-write operation. Default FAIL_ON_CONFLICT; any failed field/reference validation rejects whole batch.

## Implemented gate sequence (planned, not completed)

| Gate | Work package | Acceptance cases |
|---|---|---|
| P6-G0 | ADR-039..048 and architecture | No code, design review + exact-main CI |
| P6-G1 | L6.1 Provider & Deployment Domain | P6-AC-001..008 |
| P6-G2 | L6.2 Registry Ports & InMemory | P6-AC-009..016 |
| P6-G3 | L6.3 Queries & Catalog Search | P6-AC-017..024 |
| P6-G4 | L6.4 Effective Capability & Limits | P6-AC-025..032 |
| P6-G5 | L6.5 Deployment Resolution | P6-AC-033..040 |
| P6-G6 | L6.6 Offline Discovery & Merge | P6-AC-041..048 |
| P6-G7 | L6.7 Integration & Quality | P6-AC-049..056 |

Final M6 technical review is separate from P6-G7, and neither confers release permission. Each implementing lot starts only when its predecessor architecture gate is qualified per the project governance; evidence must refer to exact branch/main SHA and runs.

## Review risks
- UNKNOWN vs NOT_APPLICABLE ambiguity: enforce explicit applicability evidence.
- PARTIAL/EMULATED cannot be ordered with naive enum minimum.
- InMemory separate ports may require coordinator for actual batch atomicity.
- `main` currently reports `protected:false` (issue #22); issue #35 and #36 remain open.
- A green PR check is not a post-merge main check; do not declare GO without the latter.

## Qualification scope
This document specifies contracts only. It is **not** a claim that P6 code, acceptance tests, a provider adapter, M6 GO or release `0.1.0b2` exists.
