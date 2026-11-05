# M2 - Interaction Foundations Qualified - Decision Record

> **Decision: M2 = GO, engineering/source candidate (2026-11-05).**
> **Release/publishing decision:** **NOT AUTHORIZED / NOT PERFORMED.**
> **Version metadata:** `0.1.0a2`, unpublished candidate.
> **Project:** PyLLMKit (Python >=3.11, provider-agnostic domain)
> **Decision basis:** Qualified integration of G0, G1, G2, G3 and G4.
> **Qualified `main` SHA:** [`560d3a46c74cecebdf6a55301b2b8ca4e34331d4`](https://github.com/tawounfouet/pyllmkit/commit/560d3a46c74cecebdf6a55301b2b8ca4e34331d4)
> **CI after integrated documentation:** [#42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) - **SUCCESS**
> **Qualification assessment:** Technical evaluation by assistant of repository, owner-approved architecture decisions and CI evidence; **not** a separate independent human GitHub approval.
> **Archive:** This record is committed through a separate PR. Verify the new post-report `main` SHA and CI and append proof to the archival PR. No future SHA is pre-validated by this report.

## 1. Executive M2 verdict

**GO for the source-controlled, installable `0.1.0a2` candidate.** The Interaction Domain can now represent and serialize text-only (AC-006) and ordered text/image (AC-007) messages without provider SDK, credentials, network I/O or a mandatory Conversation aggregate. This is a DDD Value Object and provider-agnostic domain modeling milestone, not an inference engine or API integration milestone.

The version has **not** been tagged or released on GitHub and has **not** been uploaded to PyPI. The decision to publish, select a distribution channel, sign release artifacts or make support guarantees is separate.

## 2. G0-G4 evidence chain

| Gate | Outcome | Evidence |
|---|---|---|
| G0 - Architecture Ready | GO | Owner accepted ADR-008..ADR-013; [PR #8](https://github.com/tawounfouet/pyllmkit/pull/8), [G0 record](P2_BOOT_GATE_REVIEW.md) |
| G1 - Content & Message Ready | GO | [PR #11](https://github.com/tawounfouet/pyllmkit/pull/11) + [PR #12](https://github.com/tawounfouet/pyllmkit/pull/12); AC-006; [G1 record](P2_G1_GATE_REVIEW.md) |
| G2 - Multimodal Ready | GO | [PR #14](https://github.com/tawounfouet/pyllmkit/pull/14); AC-007; [G2 record](P2_G2_GATE_REVIEW.md) |
| G3 - Quality Ready | GO | [PR #16](https://github.com/tawounfouet/pyllmkit/pull/16); Interaction JSON v1; [G3 record](P2_G3_GATE_REVIEW.md); main SHA `fb4760aa890dceb8c08b16738500b5b28574e60b`, CI [#42015194077](https://github.com/tawounfouet/pyllmkit/actions/runs/42015194077) SUCCESS |
| G4 - Integration Ready | GO | [PR #17](https://github.com/tawounfouet/pyllmkit/pull/17) documented G3, synchronized API/README/roadmap/traceability and merged; final integrated SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`, [main CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) SUCCESS |

Documentation PRs #9, #10, #13 and #15 archived earlier gate evidence; their merge histories and CI are linked in the respective gate reviews. All implementation PRs listed above have been merged into `main`.

## 3. Exact-SHA test, build and compatibility evidence

| Qualification | Result | Verification |
|---|---|---|
| Commit | `560d3a46c74cecebdf6a55301b2b8ca4e34331d4` | GitHub main branch |
| CI | **SUCCESS** | [#42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) |
| Python 3.11 / 3.12 / 3.13 | **3/3 SUCCESS** | CI job matrix |
| Pytest | **342 passed, 0 failed** | Python 3.11 job log |
| Branch-inclusive combined coverage | **91%** | Python 3.11 job log; no invented minimum |
| Ruff | **PASS** | Python 3.11 job log |
| mypy strict | **PASS**, **26 source files** | Python 3.11 job log |
| Offline examples | **PASS** | Including `L2.4 Interaction JSON round-trip: OK` |
| Wheel build | **PASS** | `pyllmkit-0.1.0a2-py3-none-any.whl` |
| Sdist build | **PASS** | `pyllmkit-0.1.0a2.tar.gz` |
| Wheel and sdist clean-install smoke | **PASS** | CI executes Interaction round-trip from isolated installs |
| Model/Artifact codec v1 regression | **PASS** | Existing M1 suite included unchanged |
| GitGuardian | **SUCCESS** on PR #16 and #17 heads | Security check; not exhaustive certification |
| Dependencies | **No mandatory provider SDK** | `pyproject.toml` and dependency tests |

## 4. Definition of Done M2

- [x] `Role`, `Message`, `ContentPart`, `TextContent`, `Content`, `MediaSourceRef`, `ImageContent` importable from public domain paths.
- [x] Message and Content required cardinality enforced, content ordering and duplicates retained.
- [x] Five canonical roles, invalid role rejected without implicit provider fallback.
- [x] TextContent and ImageContent are typed immutable Value Objects.
- [x] AC-006 and AC-007 acceptance tests pass, including JSON round-trips.
- [x] INT-001..009 and relevant MOD-003/005 tests mapped to evidence; INT-010/011 implementations explicitly deferred by ADR-013.
- [x] Conversation is not needed and remains intentionally deferred.
- [x] Independent Interaction JSON codec v1 strict on schema/parts/roles/sources; M1 codec unaffected.
- [x] Domain Core is standard-library based with targeted import fitness and offline tests.
- [x] All M1 baseline tests remain green as part of 342-test full suite.
- [x] CI matrix, strict typing, lint and isolated wheel/sdist builds successful.
- [x] README, API, JSON schema, examples, changelog and traceability synchronized on integrated main.
- [x] ADR-008..ADR-013 accepted by explicit owner decision at G0.
- [x] Implementation and documentation PRs integrated and exact main SHA CI SUCCESS.
- [x] M2 technical decision and qualified SHA recorded here.

## 5. Functional test evidence

| Requirement | Evidence | Status |
|---|---|---|
| AC-006 | `tests/acceptance/test_ac_006_text_message.py`, `test_ac_006_007_roundtrip.py` | PASS |
| AC-007 | `tests/acceptance/test_ac_007_multimodal_message.py`, `test_ac_006_007_roundtrip.py` | PASS |
| INT-003/005/008 | `test_content.py`, `test_text_content.py`, serialization tests | PASS |
| INT-004/006/007 | `test_role.py`, `test_message.py`, negative codec tests | PASS |
| INT-009 | `test_media_source_ref.py`, `test_image_content.py`, URI/asset codec tests | PASS |
| MOD-003/005 | Typed text/image modality tests and no-conversion boundaries | PASS |
| Interaction schema v1 | `tests/serialization/test_interaction_codec.py` + extension refusal tests | PASS |
| M1 schema v1 | Existing Model/Artifact codec tests | PASS |
| INT-010/011 beyond text/image | Deferred by accepted ADR-013 | NOT IN SCOPE |

## 6. Architecture interpretation and constraints

- **DDD:** Message, Content, TextContent, ImageContent and MediaSourceRef are immutable Value Objects. Identity, persistence and Conversation aggregate lifecycles are not introduced by convenience.
- **Open-Closed Principle:** New content kinds require an explicit, versioned codec extension; unregistered subclasses are rejected instead of being silently flattened.
- **Separation of Concerns / Ports & Adapters:** The Interaction domain does not own provider SDKs, network access, media resolution, authorization, policy or inference engines.
- **Backward compatibility:** M1 Model and Artifact v1 serialization is unaffected; Interaction schema version numbering is independent. M1 pre-release backward-reading behavior is not misrepresented as a universal round-trip guarantee.
- **Security:** The URI validator is syntactic only; future adapters must enforce SSRF, IP/DNS policy, redirect rules, MIME/payload limits and access control. JSON mappings include complete URI source values because exact round-trip is required, so logging must redact them.
- **JSON parser boundary:** The codec accepts parsed mappings. The default `json.loads` behavior with duplicate keys is outside its control and must be guarded at a stricter transport boundary if relevant.
- **Governance:** GitHub reported `main` unprotected; no independent GitHub review or external security audit is claimed. A separate protections policy is recommended before publication.
- **Packaging:** `0.1.0a2` version metadata describes only an installable development candidate. Builds are not evidence of a package being published.

## 7. NO-GO triggers checked

None of the required NO-GO conditions were observed on the qualified SHA: invalid role fallback, empty Content accepted, ordering loss, media I/O, provider dependency, M1 regression, failing required CI, missing integrated SHA evidence, or false publication claims.

This observation is bounded by the test matrix and documented architecture checks; it is not a universal formal proof of program correctness or complete security.

## 8. Decision boundaries

**M2 = GO for Interaction Foundations Qualified** as a technical source milestone on `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`.
**Publishing `v0.1.0a2` = NOT AUTHORIZED / NOT PERFORMED**.

Suggested next increments: `0.1.0a3` Inference Primitives (design and independent ADR review first), optional branch protections/required checks, and an explicit release go/no-go if publication is requested. Do not treat M2 GO as permission to publish.

## 9. Archival integrity

This gate report is created on a branch based on already-qualified `main` SHA `560d3a46c74cecebdf6a55301b2b8ca4e34331d4`, [CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424). The archival merge itself creates a new SHA. Its CI must be verified before declaring that the **M2 review document was integrated and qualified**. The final exact SHA and run belong in the archival PR discussion, not as an invented value in advance.
