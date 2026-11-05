# PyLLMKit - Phase 2 G3 Quality Ready - Gate Review

> **Verdict: G3 = GO** (2026-11-05)
> **Scope:** L2.4 strict Interaction JSON v1, AC-006/007 round-trips and Phase 1 non-regression
> **Qualified integrated main SHA:** [`fb4760aa890dceb8c08b16738500b5b28574e60b`](https://github.com/tawounfouet/pyllmkit/commit/fb4760aa890dceb8c08b16738500b5b28574e60b)
> **Post-merge main CI:** [#42015194077](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077) - **SUCCESS**
> **Implementation PR:** [#16](https://github.com/tawounfouet/pyllmkit/pull/16) - MERGED
> **Prior gates:** G0/G1/G2 GO and archived separately
> **Remaining gates:** G4 integration documentation and formal M2 GO/NO-GO still require post-archive CI
> **Alpha metadata:** `0.1.0a2` is a candidate in the repository, **not published**.

## 1. Technical decision

**G3 GO** is supported by full CI evidence on an integrated `main` commit after PR #16. The new Interaction codec is independent from the M1 Model/Artifact codecs, and supports reversible text/image content using schema v1 (ADR-012). It rejects unknown fields, invalid roles and versions, unsupported content kinds and malformed media sources with `DomainValidationError`.

This decision covers **L2.4 Quality Ready**, not release authorization or the separate M2 integration approval. The archival PR needs its own main CI before G4/M2 are pronounced.

## 2. Evidence

| Verification | Result | Evidence |
|---|---|---|
| PR #16 | MERGED | https://github.com/tawounfouet/pyllmkit/pull/16 |
| Integrated main SHA | `fb4760aa890dceb8c08b16738500b5b28574e60b` | Commit link above |
| GitHub Actions | SUCCESS | [Main CI #42015194077](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077) |
| Python matrix | 3.11 / 3.12 / 3.13: **3/3 SUCCESS** | CI jobs |
| Pytest | **342 passed**, no failures | Python 3.11 job log |
| Combined branch coverage | **91%** | Python 3.11 job log; not a contractual threshold |
| Ruff lint | PASS | Python 3.11 job log |
| mypy strict | PASS, **26 source files** | Python 3.11 job log |
| Offline example | `L2.4 Interaction JSON round-trip: OK` | Python 3.11 job log |
| Wheel + sdist | `pyllmkit-0.1.0a2` builds PASS | CI |
| Isolated wheel/sdist smoke | Imports and Message round trip PASS | CI |
| GitGuardian security checks | SUCCESS on PR #16 head | PR checks |
| M1 Model/Artifact serialization | Existing tests pass unchanged | Full regression suite |

Earlier candidate commits failed Ruff import sorting and mypy redundant-cast checks, and were fixed on later commits. **Only the final green head and integrated main CI qualify this gate.**

## 3. Requirement evidence

| Requirement | Verified tests | Outcome |
|---|---|---|
| AC-006 | `tests/acceptance/test_ac_006_text_message.py`, `test_ac_006_007_roundtrip.py` | PASS, text -> dict -> JSON -> Message |
| AC-007 | `tests/acceptance/test_ac_007_multimodal_message.py`, `test_ac_006_007_roundtrip.py` | PASS, text/image order and values |
| ADR-012 Interaction codec | `tests/serialization/test_interaction_codec.py` | PASS, independent version 1 and strict input |
| ADR-010 extension policy | `tests/serialization/test_interaction_codec_extension.py` | PASS, unknown concrete parts rejected |
| ADR-011 media sources | `test_interaction_codec.py`, `test_media_source_ref.py` | PASS, URI and asset preserving round-trip |
| INT-003/005/008 | `test_content.py`, `test_text_content.py` and codec tests | PASS, empty text valid, Content nonempty |
| INT-004/006/007 | `test_role.py`, `test_message.py` and codec errors | PASS, canonical roles and explicit invalid-role errors |
| MOD-003/005 | `test_image_content.py`, `test_ac_006_007_roundtrip.py` | PASS, modality reflects typed content, no conversion |
| M1 backward behavior | Existing `tests/serialization` and `tests/acceptance` | PASS, Model codec v1 untouched |

## 4. Explicit constraints and residual risk

- `message_from_dict` expects an already parsed mapping. Standard `json.loads` may silently overwrite duplicate JSON keys. Reject duplicates in caller parsing when required.
- Strict validation rejects unknown/missing schema fields, kinds and malformed values, without echoing sensitive user-supplied media URI values in domain errors.
- Encoded mappings **do contain complete media URIs** to guarantee round-trip; redact before logging. No media is fetched; syntactic URI validity is not SSRF safety.
- `Conversation`, `InferenceRequest`, provider SDKs, audio/video/document and tool content remain deferred.
- G3 is not a security certification or guarantee of transport isolation: offline fixture and AST import checks are targeted quality gates.
- `main` is not branch-protected. Later release/publishing requires governance review and separate explicit authorization.
- No independent GitHub reviewer approval is asserted. PR checks and owner-authorized engineering work are the qualification evidence.
- `0.1.0a2` is a **repository build candidate**, not an uploaded package. No Git tag, GitHub Release or PyPI action has been taken.

## 5. Next gate

Update README, API reference, phase traceability and M2 review record to reflect L2.4 integration. Merge these documents, capture exact new `main` SHA and CI. If no issues remain, assess **G4 Integration Ready**, then issue the formal **M2 GO/NO-GO** on that qualified commit, independently of publication.
