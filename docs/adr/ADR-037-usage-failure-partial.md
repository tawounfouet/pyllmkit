# ADR-037 - Usage, Failures & Partial Evidence

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

UsageUpdated carries M3 Usage snapshot and is_final exact boolean. Unknown counts remain None, not 0; a latest snapshot is not automatically final. FAILED and CANCELLED preserve partial text and calls but cannot imply COMPLETED. Diagnostic codes and repr must never expose raw content.

## Why this decision

Usage is not a cost and must not be summed as cumulative deltas.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-029, AC-030, AC-039. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
