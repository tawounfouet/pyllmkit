# ADR-011 - Passive typed media sources and security boundary

- **Status:** ACCEPTED for Phase 2 design (P2-BOOT, 2026-11-05). Implementation and M2 qualification remain pending.
- **Authorization:** Explicit review and approval by the repository project owner in the PyLLMKit project conversation on 2026-11-05. This is an owner decision, not a GitHub review submission or independent architecture audit.
- **Decision effective date:** 2026-11-05.
- **Context:** ImageContent needs an explicit reference to media without forcing network access, file reads or large bytes into a domain value object.
- **Sources:** specifications 07 (INT-009, MOD-005), Phase 2 plan sections 5 and 10, domain-first principle.

## Decision
1. Introduce a frozen `MediaSourceRef` Value Object with discriminated source kinds: `uri` or `asset`. An image requires exactly one valid `MediaSourceRef`.
2. A URI source stores an absolute HTTP(S) URL with a syntactically valid host. Validation is syntactic only: **no DNS resolution, GET/HEAD, file access or media decoding**. A URI being syntactically valid does not mean it is trusted or reachable.
3. An asset source stores a nonblank opaque identifier. It has no built-in storage provider, resolver or filesystem semantics.
4. Explicitly exclude `file://`, local paths, `data:` URIs, arbitrary schemes, inline bytes and embedded base64 in a2. Their necessity and constraints require later ADRs.
5. Do not automatically log or emit user-provided full URIs in exception messages or representations intended for telemetry. Adapter layers must enforce URL policy, allowlists, size limits, SSRF defenses, authentication, and content checks before accessing external media.
6. `ImageContent` retains source reference only and reports `Modality("image")`; it does not imply OCR, image generation or vision capability.

## Alternatives
- Inline `bytes` in Value Objects: rejected for unbounded size, serialization and security cost.
- `ImageContent(url: str)` only: rejected, does not support asset registry references.
- Domain-side download or MIME sniffing: rejected, violates separation of concerns and offline guarantees.

## Consequences
- A2 can represent both trusted external assets and supplied HTTP(S) URIs without I/O.
- Future provider adapters own materialization and security policy; a2 validates structure only.
- Codec serializes the reference kind and value without loading content.

## Acceptance Tests
- Valid `uri` and `asset` references round-trip.
- Missing/blank asset, invalid scheme, missing URI host or multiple conflicting sources fail.
- Construction/serialization are offline with network/file access disabled.
- No secret-bearing URLs appear in validation errors or CI logs.
- `INT-009`, `MOD-003`, `MOD-005` remain traceable.

## Follow-ups
- L2.3: implement and test two source kinds and ImageContent.
- Provider adapters in 0.2.x: explicit transport/SSRF/media policies.
