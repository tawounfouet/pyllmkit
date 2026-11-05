# ADR-031 - StreamEvent Identity & Ordering

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

Every event requires an explicit M3 InferenceRunId and an exact integer sequence 0..2**63-1 (bool rejected). ResponseStarted is sequence 0; each subsequent event has sequence previous+1. The pair (run_id, sequence) uniquely identifies position. No sorting, hidden IDs or clock-based ordering.

## Why this decision

Native provider sequence numbers must be mapped explicitly at a future boundary.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-009..013. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
