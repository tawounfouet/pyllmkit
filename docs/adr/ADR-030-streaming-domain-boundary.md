# ADR-030 - Streaming Domain Boundary

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

InferenceStream is a typed, behavioral protocol, not an Entity or duplicate InferenceRun. StreamEvent is an immutable Value Object. No SDK, transport, I/O, network, or executor in domain.streaming.

## Why this decision

An Iterator[str] loses structure; duplicating the InferenceRun aggregates violates DDD.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-001, AC-002, AC-008. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
