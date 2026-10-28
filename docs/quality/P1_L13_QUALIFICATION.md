# P1-L13 - Quality & Testing qualification dossier

> **Status:** PASS - QUALIFIED for M1, 2026-10-28. Exact SHA evidence in `M1_GATE_REVIEW.md`.
> **Source of truth:** `docs/01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md`, §7 and §10.
> **Release version:** `0.1.0a1` is a *candidate version metadata*, not a publication.

## Scope

L1.3 qualifies the **provider-independent Domain Core** delivered by L1.1 and L1.2. It does not qualify inference, deployment, endpoints, providers, routing, RAG, tools execution or the complete MVP.

## Task-to-evidence matrix

| Task | Required result | Evidence in this branch | State |
|---|---|---|---|
| P1-L13-T01 | Installable `src/` project | `pyproject.toml`, `src/`, CI install | PASS on integrated main CI #40638326259 |
| P1-L13-T02 | Pure fast pytest fixtures | `tests/conftest.py`, `tests/unit/` | PASS on integrated main CI #40638326259 |
| P1-L13-T03 | Lint & typing | Ruff + mypy strict, Python 3.11–3.13 | PASS on integrated main CI #40638326259 |
| P1-L13-T04 | DDD identity vs VO semantics | `tests/unit/domain/models/` | Already exercised upstream; recheck |
| P1-L13-T05 | MODEL/CAP/MOD negatives and unknown | Domain & acceptance tests | PASS on integrated main CI #40638326259 |
| P1-L13-T06 | Versioned JSON roundtrip | `tests/serialization/` | Already exercised upstream; recheck |
| P1-L13-T07 | No provider/HTTP/secret deps | `tests/architecture/guard.py`, negative guard tests | PASS on integrated main CI #40638326259 |
| P1-L13-T08 | Offline core tests | Autouse socket blocker & env masking | PASS on integrated main CI #40638326259 |
| P1-L13-T09 | Concepts + API + runnable examples | `README.md`, `docs/api/domain.md`, `examples/` | PASS on integrated main CI #40638326259 |
| P1-L13-T10 | Build/install wheel + sdist | Clean venv smoke checks in CI | PASS on integrated main CI #40638326259 |
| P1-L13-T11 | Release note + traceability | This dossier, `PHASE_1_TRACEABILITY.md`, gate report | PASS: M1 GO recorded |

## Reproducible qualification commands

```bash
python -m pip install -e '.[dev]'
python -m ruff check .
python -m mypy src/pyllmkit
python -m pytest -q --cov=pyllmkit.domain --cov-branch --cov-report=term-missing --cov-report=xml
python examples/01_define_model.py
python examples/02_define_artifacts.py
python examples/03_define_capabilities.py
python -m build
```

In GitHub CI, wheel and sdist are each installed into separate fresh virtual environments and checked via standalone domain imports.

## Quality rules

- **Zero blocking lint, type errors, or test failures.** No exceptions for critical invariants.
- **Coverage report required, but no arbitrary coverage threshold**: the Phase 1 source plan §7.5 explicitly treats a percentage target as a governance option still to be approved.
- **AST import guard:** blocks known forbidden dependencies, including some relative and literal dynamic imports. Does not claim to detect obfuscated or constructed dynamic imports.
- **Offline fixture:** rejects socket `connect`, `connect_ex`, `bind`, `create_connection` within each pytest case and clears common LLM keys; this is not an OS-level network sandbox, and cannot prove third-party modules are absent.
- **Fresh install:** wheel and sdist smoke import packages after build, without depending on local `src/` path.
- **No publication and no git tags** are triggered by the workflow.

## Governance items (resolved for M1; separate publication checks remain)

1. Review and accept/change ADR-001 through ADR-006 (all currently PROPOSED).
2. Review / merge stacked PR #1 -> #2 -> #3 -> #4 only when accepted.
3. Decide the public license and release policy.
4. Set / waive explicit branch-coverage threshold by ADR if desired.
5. Review exact head SHA, CI run links, build artifact evidence and traceability, then record M1 GO or NO-GO.

**M1: GO recorded on 2026-10-28, based on CI green at integrated `main` SHA `4aaf4c91e97ff7dfc3d0f2c6164c3cd88fe2923a`. Publication not performed.**
