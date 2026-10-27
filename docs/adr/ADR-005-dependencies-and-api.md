# ADR-005 - Dependencies, package layering and public API

- **Status:** PROPOSED.
- **Decision:** Python >=3.11, src layout, setuptools PEP 517, stdlib-only runtime dependencies, typed internal packages.
- **Decision:** Defer stable domain re-exports until L1.1/L1.2 domain APIs exist. Provider integrations remain optional.
- **Acceptance:** provider-free imports, architecture guards, lint, typing, tests and builds in CI.
- **Sources:** specs 01, 02, 03.
