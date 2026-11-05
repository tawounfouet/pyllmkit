# P5-G0 - Architecture precheck

- Date: 2026-11-05
- Status: PRECHECK, NOT QUALIFIED GO
- Baseline: c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Verified design inputs

- [x] M3 identifiers and Usage and M4 ToolCallId / ToolArguments / ToolCall inspected.
- [x] ADR-030 through ADR-038 drafted with explicit, testable decisions.
- [x] ToolCallDelta selected as the canonical streamed raw argument fragment.
- [x] Strict 0-based contiguous sequence and run correlation defined.
- [x] Cancellation distinguished from failure and completion; INCOMPLETE is nonterminal evidence.
- [x] Pure reducer, provider-free sync/async ports and isolated JSON codec documented.
- [x] Memory limits and no raw payload in diagnostics.
- [ ] Architecture PR merged to main.
- [ ] GitHub Actions push/main CI passed on exact qualifying SHA.
- [ ] P5-G0 signed gate record with evidence archived.

## Governance

This precheck is not an implementation, not a release and not proof of a running provider adapter. Do not change pyproject version or ship 0.1.0b1. Issues #22, #35 and #36 remain open constraints.
