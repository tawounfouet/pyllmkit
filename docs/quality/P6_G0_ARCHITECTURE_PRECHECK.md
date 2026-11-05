# P6-G0 - Architecture precheck

> **Précheck historique de candidature.** La qualification actuelle est consignée dans [`P6_G0_GATE_REVIEW.md`](P6_G0_GATE_REVIEW.md) et dans la revue finale [`M6_GATE_REVIEW.md`](M6_GATE_REVIEW.md). Les cases « pending » ci-dessous représentent l'état à la création du document, pas l'état actuel.


- Date: 2026-11-05
- Status: DESIGN PRECHECK / PENDING QUALIFICATION (not GO)
- Repository: tawounfouet/pyllmkit
- Initial main SHA: 19cc1c9e1d5598711890ddc3e14f1da94c79ce70
- Source version: `0.1.0a2`
- Target: Phase 6 Registry & Discovery / M6

## Evidence inspected

- [x] User-supplied P6 implementation plan and foundational design files 00..09.
- [x] GitHub main commit `19cc1c9e1d5598711890ddc3e14f1da94c79ce70`, post-M5, reviewed.
- [x] `Model`, `ProviderModelRef`, `ModelId`, `DeploymentId`, `ModelTarget`, `DeploymentTarget`, `CapabilitySet`, `CapabilitySupport`, `ModelLimits` inspected on main.
- [x] Existing ADR series ends at ADR-038 at baseline; ADR-039..048 reserved for P6.
- [x] Ten P6 ADR proposals and architecture note authored on dedicated P6-G0 branch.
- [x] P6 L6.1..L6.7 dependencies, evidence requirements, 56 AC targets inventoried.
- [x] Boundaries: ProviderCatalog != AdapterRegistry; no SDK/network/inference/physical endpoint.
- [x] Idempotence requires complete Model snapshot, not identity-only equality.
- [x] UNKNOWN vs NOT_APPLICABLE and PARTIAL vs EMULATED addressed explicitly.
- [ ] Owner/design review has accepted ADR-039..048.
- [ ] P6-G0 architecture PR has been merged to main.
- [ ] Successful post-merge GitHub Actions push/main run on **exact merged main SHA**.
- [ ] Final P6_G0_GATE_REVIEW record cites verifiable CI and design acceptance.

## Decision
**NO GO DECLARED YET.** Authoring a draft and opening a PR is not technical qualification. Do not begin implementing P6 on main until G0 acceptance + post-merge proof, do not merge P6 code here and do not tag or publish `0.1.0b2`. Pending governance: main unprotected (issue #22), release (issue #35) and provider boundary (issue #36).
