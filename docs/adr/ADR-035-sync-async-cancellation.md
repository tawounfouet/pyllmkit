# ADR-035 - Sync/Async & Resource Ownership

- Date: 2026-11-05
- Status: ACCEPTED FOR DESIGN, P5-G0 technical gate pending
- Phase: P5 Streaming, target milestone M5
- Baseline: main@c896cbf22bf7893f8a0eb722c9fc3db641ed624b

## Decision

Separate protocols stream(request)->Iterator[StreamEvent] and astream(request)->AsyncIterator[StreamEvent]. The latter returns an async iterator directly, not a coroutine requiring await before async for. Pull-based, offline semantics only. The stream producer owns cleanup; explicit close/aclose applies when appropriate. Early closure cannot imply ResponseCompleted.

## Why this decision

Do not impose asyncio on sync consumers; no network-level backpressure claim.

## Invariants and boundaries

Core remains domain-first, provider-agnostic, offline, strictly typed and deterministic. No SDK, HTTP, executable tool handler or provider assumptions may enter this domain. Errors and repr must not disclose raw text, raw arguments or secrets. Existing M1-M4 JSON v1 contracts remain unchanged.

## Verification

AC-025..032. Include negative tests, architecture fitness checks and Python 3.11/3.12/3.13 CI in the implementing lot.

Design acceptance does not itself qualify P5-G0: the gate requires successful CI on the exact merged main SHA.
