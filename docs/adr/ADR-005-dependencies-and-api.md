# ADR-005 - Dependencies, package layering and public API

- **Status:** ACCEPTED for Phase 1 alpha (2026-10-28), under delegated milestone-completion authorization; independent reviewer signature not asserted.
- **Decision:** Python >=3.11, src layout, setuptools PEP 517, stdlib-only runtime dependencies, typed internal packages.
- **Decision:** Defer stable domain re-exports until L1.1/L1.2 domain APIs exist. Provider integrations remain optional.
- **Acceptance:** provider-free imports, architecture guards, lint, typing, tests and builds in CI.
- **Sources:** specs 01, 02, 03.

## Alpha import contract

Both `from pyllmkit.domain import Model, ModelId, ModelIdentity, ModelFamily` and imports from `pyllmkit.domain.models` / `capabilities` / `modalities` / `errors` are supported by source reexports and acceptance tests. This is a typed domain facade, not an inference or provider client. Its symbols may evolve in later alphas with explicit change log entries.
