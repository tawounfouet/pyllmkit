# ADR-002 - Entities and value objects lifecycle

- **Status:** PROPOSED.
- **Decision:** VOs default to frozen dataclasses; Model is an Entity identified by ModelId. Metadata may evolve without changing Entity identity.
- **Alternatives:** mutable public dataclass structural equality is discouraged. Immutable snapshots with explicit transitions remain possible.
- **Acceptance:** VO value equality, Entity identity equality, forbidden accidental mutation.
- **Sources:** specs 05, 07.
