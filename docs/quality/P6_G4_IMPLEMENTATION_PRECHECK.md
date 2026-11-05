# P6-G4 - L6.4 Effective Capability & Limits candidate

> **Précheck historique de candidature.** La qualification actuelle est consignée dans [`P6_G5_GATE_REVIEW.md`](P6_G5_GATE_REVIEW.md) et dans la revue finale [`M6_GATE_REVIEW.md`](M6_GATE_REVIEW.md). Les cases « pending » ci-dessous représentent l'état à la création du document, pas l'état actuel.


- Date: 2026-11-05
- Status: DRAFT / NOT QUALIFIED
- Branch: p6/l64-effective-capability-limits
- Base: PR #62 (P6-G3 candidate), precondition PR #59-62 merge and exact-main qualification

## Pure implementation
- CapabilityResolver resolves Model, Deployment and optionally Provider declarations with source evidence.
- UNKNOWN (level None) remains different from UNSUPPORTED; only structurally absent local provider is NOT_APPLICABLE.
- UNSUPPORTED vetoes even UNKNOWN; PARTIAL+EMULATED remains PARTIAL with emulation disclosure.
- Constraint reduction uses explicit max/min, boolean restriction, allowed-values intersection, exact-scalar policy; unknown or conflicting policies are reported rather than guessed.
- LimitResolver computes the most restrictive known ModelLimits, preserving per-source evidence and flags provisional vs confirmed bounds.
- M1 CapabilitySet.intersection, ModelLimits, M3 CompatibilityReport and M1-M5 codecs remain unchanged.
- No SDK, network, provider adapter, persistence, healthcheck or inference invocation.

## Evidence pending
- [ ] P6-AC-025..032 tests, negative cases and source-order reproducibility reviewed.
- [ ] Python 3.11/3.12/3.13 CI: Ruff, mypy strict, branch coverage >=95%, wheel/sdist.
- [ ] Predecessor PRs #59-62 and exact-main gates qualified.
- [ ] Review/merge P6-G4 and verify push/main CI on exact merged main SHA.

No release or tag authorized. Version stays 0.1.0a2.
