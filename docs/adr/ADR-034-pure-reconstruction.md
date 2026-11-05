# ADR-034 - Pure Reconstruction & Validation

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

Reduce an immutable StreamState with one StreamEvent and return a new state. Preserve exact text fragments and per-ID tool argument fragments. A closed call may be assembled into M4 ToolCall with ToolArguments(raw=...) and has_parsed=False. Never manufacture ToolResult, StructuredOutput VALID, or InferenceResponse.

## Why this decision

Do not repeatedly concatenate accumulated strings in the reducer; retain chunks for efficient final joining.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-016, AC-018, AC-022, AC-023, AC-030. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
