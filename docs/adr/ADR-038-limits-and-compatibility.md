# ADR-038 - Resource Limits & Compatibility

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

Initial bounded profile: at most 100000 events, 8 MiB of UTF-8 text, 128 distinct tool calls, at most 1 MiB of UTF-8 raw arguments per call (compatible with M4 ToolArguments). Budget failures use bounded domain errors. No mutation to M1-M4 classes, imports or codecs.

## Why this decision

No unbounded in-memory buffering; revise limits by ADR if measured performance requires it.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-024, AC-046, AC-047. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
