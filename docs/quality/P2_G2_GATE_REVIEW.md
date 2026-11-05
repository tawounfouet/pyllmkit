# PyLLMKit - Phase 2 G2 Multimodal Content Ready - Gate Review

> **Verdict: G2 = GO** (2026-11-05)
> **Scope:** L2.3 MediaSourceRef, ImageContent, ordered text/image Content and AC-007
> **Qualified integrated main SHA:** [`8e4d8c1df998d17e20e50a79b5c6904fe5de0616`](https://github.com/tawounfouet/pyllmkit/commit/8e4d8c1df998d17e20e50a79b5c6904fe5de0616)
> **Main CI after PR merge:** [#42011868937](https://github.com/tawounfouet/pyllmkit/actions/runs/42011868937) - **SUCCESS**
> **Implementation PR:** [#14](https://github.com/tawounfouet/pyllmkit/pull/14) - MERGED
> **Prior gate:** [G1 - Content & Message Ready](P2_G1_GATE_REVIEW.md)
> **Milestone:** **G2 GO**, L2.4 codec/G3/G4/M2 still PENDING
> **Publication:** `0.1.0a1` remains an unpublished alpha candidate; no release authorized.

## 1. Verdict and rationale

The repository now represents text and images as genuinely typed, ordered, provider-agnostic domain content, without downloading, opening, decoding, or sending media. `AC-007` is covered by an executable test and an offline example. L2.3 has passed CI after squash merge into `main` on the exact SHA above.

**G2 = GO** for *representing* multimodal content and passive sources. **G2 does not assert that an external URL can be safely fetched**, that a particular LLM supports vision, that JSON serialization works, or that the M2 alpha is qualified.

## 2. Implemented types

| Type / file | Contract | Relevant decision |
|---|---|---|
| `MediaSourceRef` - `domain/interactions/media.py` | Frozen/slotted VO: `kind="uri"` or `"asset"`, `value: str`; strict validation; original value preserved | ADR-011 / INT-009 |
| `ImageContent` - `domain/interactions/image.py` | Frozen/slotted `ContentPart`; required typed source; `kind="image"`; `modality=Modality("image")` | ADR-010 / ADR-011 / MOD-003 |
| `Content` - `domain/interactions/content.py` | Existing nonempty tuple now holds interleaved `TextContent` and `ImageContent` without reordering or merging | ADR-010 / INT-003 / INT-005 |
| `Message` - `domain/interactions/message.py` | Existing immutable Role + Content composition accepts ordered text/image/text | ADR-009 / AC-007 |
| Public exports | `pyllmkit.domain.interactions` and `pyllmkit.domain` expose new symbols while preserving G1/M1 imports | Compatibility |

## 3. Evidence on integrated main

| Check | Verified result |
|---|---|
| PR #14 | MERGED |
| SHA integrated in main | `8e4d8c1df998d17e20e50a79b5c6904fe5de0616` |
| GitHub Actions on integrated main | [#42011868937](https://github.com/tawounfouet/pyllmkit/actions/runs/42011868937) SUCCESS |
| Python matrix | **3/3 SUCCESS** - 3.11 / 3.12 / 3.13 |
| pytest | **252 passed, 0 failed** |
| Combined coverage (branches included) | **90%** |
| Ruff | PASS |
| mypy strict | PASS on 25 source files |
| Offline examples | PASS, including `AC-007 multimodal Message: OK` |
| Wheel / sdist and clean-install smoke | PASS |
| GitGuardian Security Checks | SUCCESS on PR head `c7e5a1dcbc0bc94c142ba523dc4e9458cef89c65` |
| M1/G1 regression tests | PASS in complete 252-test suite |

The initial PR commit had two Ruff import-order failures. Both were fixed before merge; the accepted PR head and integrated main have passing CI. Failed earlier attempts do not count as successful qualification.

## 4. Acceptance and invariant traceability

| Requirement | Tests | Outcome |
|---|---|---|
| AC-007 | `tests/acceptance/test_ac_007_multimodal_message.py` | PASS: text/image/text in exact order, duplicates retained |
| INT-003 / INT-005 | `test_ac_007_multimodal_message.py`, existing `test_content.py` | PASS: typed nonempty ordered Content |
| INT-009 | `tests/unit/domain/interactions/test_media_source_ref.py` | PASS: typed URI/asset, invalid kind/scheme/host/port, blank asset, redacted repr |
| MOD-003 | `tests/unit/domain/interactions/test_image_content.py` | PASS: `Modality("image")` |
| MOD-005 | `test_media_source_ref.py`, `test_image_content.py`, architecture guard | PASS: no fetch/OCR or conversion at construction |
| AC-006 | Existing `tests/acceptance/test_ac_006_text_message.py` | PASS: G1 compatibility |
| ADR-013 | API/docs/source inventory | PASS for intended text/image scope; deferred modalities not advertised |
| ADR-011 media JSON round trip | Future L2.4 Interaction codec tests | **PENDING**, not falsely claimed in G2 |
| ADR-012 Interaction serialization | Future `tests/.../test_interaction_codec.py` | **PENDING** |

## 5. Media security boundaries and limitations

- Syntactic URL validation permits valid HTTP(S) hosts, including private IPs or localhost; **this is not an allowlist, DNS verification, or SSRF protection**.
- `MediaSourceRef` hides the entire source value in `repr` and avoids emitting it in its validation errors. This reduces accidental disclosure but is not a guarantee that a caller will never log `source.value`.
- The Domain Core has **no** URL-fetching or asset-resolution adapter. Future adapters must enforce SSRF defenses, network policy, redirects, authentication, content type and media size limits.
- `ImageContent` accepts **only** `MediaSourceRef`. Local paths, `file:`, `data:`, embedded base64, inline bytes and silent provider conversions are not supported.
- `Conversation`, audio/video/document, ToolCall/ToolResult and inference requests remain deferred; `Role.TOOL` only names a speaker.
- `main` was reported unprotected during G0/G1. Exact PR and integrated CI prove the qualifying commits, not a repository-wide policy.
- No GitHub review from an independent reviewer is asserted.

## 6. Next increment

Proceed with **L2.4 - Interaction JSON Codec and Qualification**, under ADR-012: `message_to_dict`, `message_from_dict`, independent `INTERACTION_SCHEMA_VERSION=1`, strict schema validation, text/image media reference round trips, malformed payload rejection and M1 codec non-regression. Then decide G3/G4 and the separate M2 GO/NO-GO.

No tag, GitHub Release or PyPI upload is authorized by G2.

## 7. Archival integrity

The G2 qualification SHA `8e4d8c1df998d17e20e50a79b5c6904fe5de0616` was verified **before** this documentation was committed. The separate archival PR will create a different `main` SHA. Verify CI on that final archive SHA and add it to the archive PR comments; do not retroactively claim the original run tested future commits.
