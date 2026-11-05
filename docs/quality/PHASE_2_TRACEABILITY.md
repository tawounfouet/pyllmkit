# Phase 2 - Requirement and evidence traceability

**Status:** P2-BOOT IN REVIEW (design only), 2026-11-05. Nothing in L2.x or M2 is marked implemented by this document.
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
| docs/02_PYLLMKIT_PHASE_2_IMPLEMENTATION_PLAN.md | This P2-BOOT branch | Copied plan, proposal pending review |
| docs/adr/ADR-008 .. ADR-013 | This P2-BOOT branch | Proposals, not accepted until decision recorded |

Do not fabricate GitHub links for draft source files absent from the repository. The user-provided documents are project references even where the GitHub repository stores only an index.

## Requirement to decision to test

| Source invariant / AC | Decision | Work item | Test target / current state |
|---|---|---|---|
| AC-006, INT-004/005/008 | ADR-008/009/010 | L2.1 + L2.2 | `test_ac_006_text_message.py` (NOT STARTED) |
| AC-007, INT-003/009 | ADR-010/011/012 | L2.3 + L2.4 | `test_ac_007_multimodal_message.py` (NOT STARTED) |
| INT-001/002 | ADR-009 | L2.1 | Message independence, sequence ordering (NOT STARTED) |
| INT-006/007 | ADR-008 | L2.1 | Invalid role/provider mapping tests (NOT STARTED) |
| INT-008 | ADR-010 | L2.2 | Empty text/None/error tests (NOT STARTED) |
| INT-009 | ADR-011 | L2.3 | URI/asset validation and no-I/O (NOT STARTED) |
| INT-010/011 | ADR-013 | Future increments | Documented deferred, no API promises |
| MOD-003/005 | ADR-010/011/013 | L2.2 + L2.3 | Modality/no-transform tests (NOT STARTED) |
| SER strict Interaction v1 | ADR-012 | L2.4 | `test_interaction_codec.py` (NOT STARTED) |
| M1 non-regression | ADR-004/005/006 | L2.4 | Existing tests + CI (BASELINE VERIFIED) |

## Release and merge discipline

- P2-BOOT branch base is recorded as the M1 commit; do not infer this is a new qualified M2 SHA.
- P2-BOOT docs and architecture test are not the implementation of Message or Content.
- Review branches and CI; no direct push to main, tag, GitHub Release or PyPI upload.
- G0 depends on explicit ADR acceptance (or revisions), not their mere presence.
- After P2-BOOT, implement L2.1/L2.2/L2.3/L2.4, then assess G0..G4 and M2 on integrated main.
