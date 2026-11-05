# P2-BOOT - Architecture gate preparation

- **Date:** 2026-11-05
- **Scope:** P2-BOOT, interaction contracts, ADR-008..ADR-013, traceability and architecture fitness baseline.
- **Status:** IN REVIEW / G0 PENDING, until ADRs reviewed and P2-BOOT PR qualified.
- **Reference main:** `d7f06072d246819fb976c6a456949995ae33562d`.
- **Main workflow:** https://github.com/tawounfouet/pyllmkit/actions/runs/40638604245 - SUCCESS (M1 baseline only).
- **Public package:** `0.1.0a1` (not published), Python >= 3.11; no provider runtime dependencies.
- **Existing M1 tests:** 137 passed / 89% coverage on old main; not proof of P2 implementation.
- **PR branch:** `feature/p2-boot-interaction-contracts`.
- **Main branch protection:** GitHub reports `protected: false` as of this audit; manual review gate required.

## P2-BOOT progress

| ID | Check | Result |
|---|---|---|
| P2-BOOT-T01 | Verify baseline SHA, CI, version and open PRs | DONE |
| P2-BOOT-T02 | Create dedicated P2-BOOT branch and six proposed ADR files | DONE on branch; review pending |
| P2-BOOT-T03 | Define Role taxonomy, unknown roles and TOOL boundary | PROPOSED ADR-008 |
| P2-BOOT-T04 | Define Message value semantics, Conversation choice | PROPOSED ADR-009 |
| P2-BOOT-T05 | Define Content polymorphism, Media refs, codec | PROPOSED ADR-010/011/012/013 |
| P2-BOOT-T06 | Define imports and public package boundaries | PROPOSED contract + architecture test |

## Decision register (draft)

| ADR | Decision summary | State |
|---|---|---|
| 008 | Five canonical roles, reject unknown, no implicit mapping | PROPOSED |
| 009 | Message VO, Conversation deferred from a2 | PROPOSED |
| 010 | Ordered nonempty Content, immutable parts, empty text allowed | PROPOSED |
| 011 | Passive URI/asset media refs, no I/O | PROPOSED |
| 012 | Strict independent Interaction schema v1, preserve M1 codec | PROPOSED |
| 013 | Text/image mandatory, audio/video/docs/tool content deferred | PROPOSED |

## Gate G0 acceptance checklist

- [x] Baseline exact SHA and main CI identified.
- [x] Proposed architecture and public contracts documented.
- [x] ADR alternatives, consequences and negative tests specified.
- [x] Source-document traceability index prepared.
- [x] No L2.x implementation pretended.
- [ ] ADR-008..013 reviewed and accepted/revised as project decisions.
- [ ] Branch CI passes on exact P2-BOOT head SHA across Python matrix.
- [ ] PR reviewed and deliberately integrated; integrated main CI verified.
- [ ] G0 verdict and responsible decision recorded after evidence.

**Verdict now: G0 PENDING / P2-BOOT IN REVIEW.** No M2 GO and no publication authorization.
