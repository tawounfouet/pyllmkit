# Phase 2 - Requirement and evidence traceability

**Status:** P2-BOOT **G0 = GO** (2026-11-05), ADR-008..013 accepted by project owner and integrated in main. G0 archive CI on SHA `0eb2d54b93eaa9375237674916504d5ab45ab373`: https://github.com/tawounfouet/pyllmkit/actions/runs/42006193308 (SUCCESS). L2.1 and L2.2 are now implemented and **G1 = GO** on `main` SHA `1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6` (CI #42008750610 SUCCESS, 204 tests, 90% combined coverage). L2.3 **implemented / G2 = GO** on `main` SHA `8e4d8c1df998d17e20e50a79b5c6904fe5de0616`, [CI #42011868937](https://github.com/tawounfouet/pyllmkit/actions/runs/42011868937) SUCCESS (252 tests, 90% coverage). L2.4 is now **integrated / G3 GO** on `main` SHA `fb4760aa890dceb8c08b16738500b5b28574e60b` ([CI #42015194077](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077), 342 tests, 91% coverage). G4 and technical M2 GO on integrated `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`, [CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) SUCCESS (342 tests, 91% coverage). M2 release/publishing is not authorized.
**Baseline evidence:** `main` d7f06072d246819fb976c6a456949995ae33562d, M1 CI https://github.com/tawounfouet/pyllmkit/actions/runs/40638604245 (success), 137 tests and 89% branch-inclusive combined coverage (Phase 1 evidence, not Phase 2 results).

## Source of truth and location

| Source | Where | Status |
|---|---|---|
| ROADMAP.md | GitHub main | Tracked; 0.1.0a2 scope exists |
| docs/01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md | GitHub main | Tracked |
| docs/quality/M1_GATE_REVIEW.md | GitHub main | M1 GO |
| docs/adr/ADR-001 .. ADR-007 | GitHub main | Accepted for Phase 1 alpha |
| 00..09_PYLLMKIT_*.md | Supplied as project source files | Foundational drafts; **NOT tracked in GitHub main** |
| PYLLMKIT_PHASE_1_POST_IMPLEMENTATION_REVIEW.md | Supplied source document | Not tracked in GitHub main |
| docs/02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md | GitHub main | Plan tracked, architecture G0 qualified |
| docs/adr/ADR-008 .. ADR-013 | GitHub main | ACCEPTED for Phase 2 design by owner on 2026-11-05 |

Do not fabricate GitHub links for draft source files absent from the repository. The user-provided documents are project references even where the GitHub repository stores only an index.

## Requirement to decision to test

| Source invariant / AC | Decision | Work item | Test target / current state |
|---|---|---|---|
| AC-006, INT-004/005/008 | ADR-008/009/010 | L2.1 + L2.2 | `tests/acceptance/test_ac_006_text_message.py` (PASS at G1) |
| AC-007, INT-003/009 | ADR-010/011/012 | L2.3 + L2.4 | `tests/acceptance/test_ac_007_multimodal_message.py` (PASS G2 for representation; JSON round-trip PASS on G3, `tests/acceptance/test_ac_006_007_roundtrip.py`) |
| INT-001/002 | ADR-009 | L2.1 | `tests/unit/domain/interactions/test_message.py` (PASS; Conversation deferred) |
| INT-006/007 | ADR-008 | L2.1 | `test_role.py` + `test_message.py` (PASS; provider adapters deferred) |
| INT-008 | ADR-010 | L2.2 | `test_text_content.py` (PASS) |
| INT-009 | ADR-011 | L2.3 | `tests/unit/domain/interactions/test_media_source_ref.py` + `test_image_content.py` (PASS G2; JSON round-trip PASS in G3) |
| INT-010/011 | ADR-013 | Future increments | Documented deferred, no API promises |
| MOD-003/005 | ADR-010/011/013 | L2.2 + L2.3 | `test_text_content.py` (G1) + `test_image_content.py` / AC-007 (G2 PASS) |
| SER strict Interaction v1 | ADR-012 | L2.4 | `tests/serialization/test_interaction_codec.py` + `test_interaction_codec_extension.py` (PASS G3) |
| M1 non-regression | ADR-004/005/006 | L2.4 | Existing M1 tests preserved, G3 integrated main CI SUCCESS (342 tests) |

## Release and merge discipline

- P2-BOOT branch base is the M1 commit; the design G0 qualification is integrated via PR #8 and archived in PR #9. The G0 GO is **not** M2 GO.
- P2-BOOT docs and architecture test are not the implementation of Message or Content.
- Review branches and CI; no direct push to main, tag, GitHub Release or PyPI upload.
- G0 depends on explicit ADR acceptance (recorded 2026-11-05), a reviewed PR and qualifying CI on the integrated main SHA, not ADR presence alone.
- G1 = GO on `main` SHA `1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6`; G2 = GO on `main` SHA `8e4d8c1df998d17e20e50a79b5c6904fe5de0616`. L2.4 and G3 GO on `main` SHA `fb4760aa890dceb8c08b16738500b5b28574e60b`. G4 and M2 qualified on `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`. See `docs/quality/M2_GATE_REVIEW.md`. Documentation archive PR requires its own final SHA CI. Publication remains a separate decision.
