# ADR-002 - Entities and value objects lifecycle

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Decision:** VOs default to frozen dataclasses; Model is an Entity identified by ModelId. Metadata may evolve without changing Entity identity.
- **Alternatives:** mutable public dataclass structural equality is discouraged. Immutable snapshots with explicit transitions remain possible.
- **Acceptance:** VO value equality, Entity identity equality, forbidden accidental mutation.
- **Sources:** specs 05, 07.

## Lifecycle contract

Entities are deliberately unhashable and use identity-based equality, even between immutable snapshots with different metadata. Value Objects are frozen and value-equal. The snapshot update methods are not mutation of the stored Entity; repositories and aggregates will be addressed in later phases.
