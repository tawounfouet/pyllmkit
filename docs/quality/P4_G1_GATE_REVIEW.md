# PyLLMKit - P4-G1 Tool Declaration Ready - Gate review

> **Decision : GO TECHNIQUE AVEC RESERVES** - 2026-11-05.
> **Qualifying main SHA :** [764809cedf4f79866757e14ed92fc9427cc87d56](https://github.com/tawounfouet/pyllmkit/commit/764809cedf4f79866757e14ed92fc9427cc87d56).
> **Qualifying push/main CI :** [#42082114438](https://github.com/tawounfouet/pyllmkit/actions/runs/42082114438), completed/success.
> **Scope :** L4.1 domain declarations only. M4, P4-G2 and release remain unqualified.

## 1. Owner authority and integration

- Owner explicitly approved PR #40 merge and continuation to L4.2 in the project conversation on 2026-11-05.
- [PR #40](https://github.com/tawounfouet/pyllmkit/pull/40) merged by squash, expected head ac5d8e8df8dd9846cb6e878144f6fbb02170551e.
- No GitHub APPROVED third-party review was present. Owner approval in chat is not a fabricated reviewer approval.
- No version bump, tag, GitHub Release, TestPyPI or PyPI.

## 2. Qualified evidence

| Check | Finding |
|---|---|
| Source baseline | main SHA 764809cedf4f79866757e14ed92fc9427cc87d56 |
| Push CI | #42082114438, completed/success on exact main SHA |
| Python 3.11 | job 127437581670 success |
| Python 3.12 | job 127437582426 success |
| Python 3.13 | job 127437582263 success |
| Tests on 3.11 | 846 passed, zero failure |
| Coverage on 3.11 | 95% global branch-inclusive; 1560 statements, 55 misses, 570 branches, 49 partial |
| Ruff | All checks passed |
| mypy strict | Success in 44 source files |
| Offline example 13 | included in source and isolated wheel/sdist CI steps |
| Wheel and sdist | CI jobs success |
| Regression M1-M3 | cumulative suite green; existing codecs unchanged |
| P4-G1 code | ToolSchema, Tool, ToolChoice, ToolChoiceKind, validate_tool_set, validate_tool_choice |
| P4-AC-001..008 | tests/acceptance/test_p4_l41_tools.py; coverage within cumulative CI |
| Architectural boundary | tests/architecture/test_p4_l41_domain_boundaries.py; domain does not execute tools |

The 846 tests are the cumulative suite; they are not all new P4 tests. The gate does not claim L4.2 call and result objects already exist.

## 3. Domain decisions and invariants

- [ADR-022](../adr/ADR-022-tool-definition-and-execution-boundary.md): tool declarations contain no executable handlers.
- [ADR-024](../adr/ADR-024-json-schema-profile-and-validation.md): bounded P4-JSON-1 profile, unknown schema keywords rejected.
- [ADR-025](../adr/ADR-025-immutable-json-raw-parsed-and-validation.md): immutable defensive schema, no raw leakage.
- [ADR-026](../adr/ADR-026-tool-choice-and-capability-semantics.md): AUTO, NONE, REQUIRED, SPECIFIC_TOOL with declared tool validation.
- No provider capability, tool execution or result is inferred.

## 4. Reservations and safety limits

- [Issue #22](https://github.com/tawounfouet/pyllmkit/issues/22): main protection ineffective (GitHub branch API protected=false), no effective governance enforcement proven.
- [Issue #35](https://github.com/tawounfouet/pyllmkit/issues/35): release approval and version remain independent and open.
- [Issue #36](https://github.com/tawounfouet/pyllmkit/issues/36): provider boundary future, not implemented.
- No independent human GitHub review; owner authority is explicit and accurately described.
- M4 stays NO CLAIM. No runtime calls, streaming execution, remote registry or provider SDK.

## 5. Decision

**P4-G1 = GO TECHNIQUE AVEC RESERVES.**

Authorize L4.2 on a distinct branch based on the qualified main. Deliver ToolCallId, ToolArguments, ToolCall, ToolResult, validation and pure result attachment; prove P4-AC-009..016, no executable tools, and preserve M1-M3.

## 6. Archival note

This gate review is being archived after the qualifying commit. The archival PR's own CI must be verified separately and must not be misrepresented as the qualifying SHA above.
