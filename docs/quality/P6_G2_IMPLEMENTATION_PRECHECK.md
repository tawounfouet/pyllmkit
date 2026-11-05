# P6-G2 - L6.2 Registry Ports & InMemory: implementation candidate

> **Précheck historique de candidature.** La qualification actuelle est consignée dans [`P6_G2_GATE_REVIEW.md`](P6_G2_GATE_REVIEW.md) et dans la revue finale [`M6_GATE_REVIEW.md`](M6_GATE_REVIEW.md). Les cases « pending » ci-dessous représentent l'état à la création du document, pas l'état actuel.


- Date: 2026-11-05
- Status: DRAFT / NOT A QUALIFIED GO
- Parent commit: `cd4f1f4675f5f78d071ca6abc78e42dc4139be01` (L6.1 candidate, PR #60)
- Design prerequisite: P6-G0 (PR #59), pending owner design acceptance / main CI

## Delivered candidate scope
- Three separate structural registry ports for Model, Deployment and Provider metadata.
- In-memory implementations backed by one private catalog state for strict referential integrity.
- `register` idempotent on identical full snapshots, rejects metadata collision including `Model.__eq__` identity-only pitfall.
- Typed `get` yields `None` when missing; `list` and `find` yield immutable, sorted tuples.
- Typed `remove` refuses deletion of Model / Provider referenced by Deployments, never cascades.
- Pure typed predicate seam for future P6 L6.3 callable query value objects.
- Acceptance scenarios P6-AC-009..016 and adversarial reference, type, collision and mutation tests.

## Qualification outstanding
- [ ] Verify CI for this candidate commit on Python 3.11, 3.12, 3.13, Ruff, strict mypy, >=95% coverage and packaging.
- [ ] Merge and qualify P6-G0 to exact main SHA (no false GO from PR-only CI).
- [ ] Merge and qualify L6.1 separately before L6.2.
- [ ] Review and merge L6.2 then verify exact-main CI and publish P6-G2 gate report.

## Scope protection
No persistence backend, discovery, capability resolver, network, SDK, physical endpoint, executable provider adapter, API keys, version bump or package publication. Version remains `0.1.0a2`.
