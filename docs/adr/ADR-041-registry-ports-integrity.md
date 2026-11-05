# ADR-041 - Registry ports, snapshots, referential integrity

- Date: 2026-11-05
- Status: ACCEPTED for P6 offline technical architecture by owner-delegated authorization, 2026-11-05 (independent GitHub review absent)
- Phase: P6 Registry & Discovery / M6
- Baseline: main@19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- References: 06_PYLLMKIT_PHASE_6_REGISTRY_AND_DISCOVERY_IMPLEMENTATION_PLAN.md; domain design 00-09; existing M1-M5 contracts.

## Decision
Introduce `ModelRegistryPort`, `DeploymentRegistryPort`, `ProviderCatalogPort` as narrow Python `Protocol` contracts. Each supports `register`, `get`, `list`, `find`, `remove`. `get` returns `None` when absent; a separate application `require_*` can raise a typed not-found error. `list/find` return immutable tuples sorted by canonical `.id.value`, never insertion order. InMemory adapters retain internal private collections and expose immutable snapshots.

Registering a new canonical ID adds it. Registering the same ID with the **same complete declarative snapshot** is a no-op. Registering the same ID with any changed field produces `RegistryConflictError`; an explicit update/merge operation is needed to change metadata. Specifically, `Model.__eq__` compares ID only and MUST NOT be used to test snapshot equality: compare all dataclass fields and nested values. Do not coerce, complete or invent IDs.

Strict catalog mutation requires the referenced Model to exist; a non-None deployment ProviderId must exist. InMemory service or aggregate coordinates these dependencies. Removing a Model or Provider referenced by a Deployment is refused; no implicit cascade. Removing a deployment removes catalog metadata only, never the underlying infrastructure.

The three ports must stay distinct from `AdapterRegistry`. Atomic **multi-registry** writes belong to L6.6's coordinated copy-on-write merge, not individual independent port calls. No hidden domain events for idempotent no-ops.

## Rejected
One mutable global dict passed to consumers; registering a referenced provider automatically; silent overwrite; rejecting all duplicate IDs even for identical snapshots.

## Verification
P6-AC-009..016, including metadata-only collision with same ModelId, reversed-insertion sorting, absent lookups, referential deletion, immutability and no network.
