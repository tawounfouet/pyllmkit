# P6-G3 - L6.3 Queries & Catalog Search candidate

> **Précheck historique de candidature.** La qualification actuelle est consignée dans [`P6_G4_GATE_REVIEW.md`](P6_G4_GATE_REVIEW.md) et dans la revue finale [`M6_GATE_REVIEW.md`](M6_GATE_REVIEW.md). Les cases « pending » ci-dessous représentent l'état à la création du document, pas l'état actuel.


- Status: DRAFT, NOT QUALIFIED
- Branch: p6/l63-typed-catalog-queries
- Depends on: P6-G0 architecture, L6.1, L6.2 exact-main qualification

## Candidate capabilities
Typed frozen ModelQuery and DeploymentQuery, explicit native-only versus usable declared capability matching, input/output modality distinction, exact provider aliases, minimum known limits and strict AND filtering. CatalogSearchService reads the existing registry ports. Return order follows L6.2 canonical ID sorting; no provider calls or mutation. AC-017..024 implemented with adversarial tests.

## Semantics / boundary
DeploymentQuery matches deployment *declarations*, not an effective Model/Provider/Deployment capability intersection. That resolver is L6.4. UNKNOWN and absent values never match strict positive criteria. No fuzzy search, fallback, cost/latency scoring, SDK or network.

## Outstanding
- [ ] CI green on candidate SHA in Python 3.11..3.13 with Ruff, mypy, tests, coverage and builds.
- [ ] Owner/architecture approval and post-merge main CI for P6-G0.
- [ ] Integrate L6.1 and L6.2 with exact-main CI proof.
- [ ] Review, merge and qualify L6.3 with exact-main CI.
- [ ] No release, tag or PyPI publish; source stays 0.1.0a2.
