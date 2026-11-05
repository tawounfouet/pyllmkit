# ADR-036 - Independent Streaming JSON v1

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

Strict envelope includes schema_version=1, object_type=stream_event, kind, run_id, sequence and payload. Exact integer version (not bool), closed kinds, required fields and no extras. Decode known events, validate traces by replay. M1-M4 JSON v1 codecs are unchanged. No raw JSON-text or SSE parser inside the domain.

## Why this decision

Separate codec prevents silent loss or schema changes in existing namespaces.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-033..040. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
