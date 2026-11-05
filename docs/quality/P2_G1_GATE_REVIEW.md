# PyLLMKit - Phase 2 G1 Content & Message Ready - Gate Review

> **Verdict: G1 = GO** (2026-11-05)
> **Scope:** L2.2 Content Domain + L2.1 Message Domain, text-only Interaction primitives
> **Qualified integrated main SHA:** [`1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6`](https://github.com/tawounfouet/pyllmkit/commit/1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6)
> **Post-merge main CI:** [#42008750610](https://github.com/tawounfouet/pyllmkit/actions/runs/42008750610) - **SUCCESS**
> **Prior gate:** [P2-BOOT G0 = GO](P2_BOOT_GATE_REVIEW.md)
> **Milestone status:** **G1 GO; G2/G3/G4 and M2 PENDING**
> **Release status:** `0.1.0a1` is still an unpublished alpha candidate; no tag, release or upload authorized.

## 1. Gate decision and scope

The Phase 2 plan defines **G1 - Content & Message Ready** as the completion of L2.1 and L2.2 with AC-006, INT-004/005/008 and regression evidence.

**G1 GO is justified:** canonical Role, Message, ContentPart, TextContent and Content are implemented, importable, validated and tested. A typed text Message is constructible offline with no required Conversation or provider SDK.

This decision qualifies the text interaction domain **only**. It does not qualify multimodal ImageContent, AC-007, the Interaction codec, M2, or publication.

## 2. Implementation and merged PRs

| Component | Implementation | Core invariant |
|---|---|---|
| `Role` | `src/pyllmkit/domain/interactions/roles.py` | Five canonical roles; invalid role rejected with `DomainValidationError` |
| `ContentPart` | `src/pyllmkit/domain/interactions/parts.py` | Abstract typed `kind` and M1 `Modality` contract |
| `TextContent` | `src/pyllmkit/domain/interactions/text.py` | Frozen/slotted VO; `str` required, empty string permitted |
| `Content` | `src/pyllmkit/domain/interactions/content.py` | Nonempty immutable ordered tuple; duplicates preserved |
| `Message` | `src/pyllmkit/domain/interactions/message.py` | Frozen/slotted VO; exactly one typed Role and Content |
| Public API | `domain/interactions/__init__.py`, `domain/__init__.py` | M1 imports retained plus new Interaction symbols |

- [PR #11](https://github.com/tawounfouet/pyllmkit/pull/11): L2.2 Content Domain - MERGED. Integrated main commit `d1d01a0ee88cab73e2c99590ee21b75ffe0ae2b4`, [CI #42008312213](https://github.com/tawounfouet/pyllmkit/actions/runs/42008312213) SUCCESS.
- [PR #12](https://github.com/tawounfouet/pyllmkit/pull/12): L2.1 Role/Message/AC-006 - MERGED. Integrated main commit `1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6`, [CI #42008750610](https://github.com/tawounfouet/pyllmkit/actions/runs/42008750610) SUCCESS.

## 3. Exact-SHA test and build evidence

| Check | Result | Evidence |
|---|---|---|
| GitHub Actions on integrated main | **SUCCESS** | CI #42008750610 |
| Python 3.11 / 3.12 / 3.13 | **3/3 SUCCESS** | CI jobs |
| pytest | **204 passed**, 0 failed | Python 3.11 job log |
| Coverage with branches enabled | **90% combined** | Python 3.11 job log; not a contractual percentage threshold |
| Ruff | **PASS** | Python 3.11 job log |
| mypy strict | **PASS**, 23 source files checked | Python 3.11 job log |
| Offline examples | **PASS** | CI (existing M1 plus 04 Content and 05 Message) |
| Wheel and sdist | **PASS**, build and clean-install smoke | CI |
| Existing M1 tests | **PASS** within full 204-test suite | CI; Model domain and codec unchanged |
| Python package metadata | Still `0.1.0a1` | `pyproject.toml` not changed |

These results are observed facts on the exact SHA listed above. No claims are made for future code, other Python versions or published wheels.

## 4. Requirement traceability

| Requirement | Test / evidence | G1 outcome |
|---|---|---|
| AC-006 | `tests/acceptance/test_ac_006_text_message.py` | **PASS** |
| INT-001/002 | `tests/unit/domain/interactions/test_message.py` (no mandatory Conversation, ordered messages) | **PASS for scoped behavior** |
| INT-003 | `tests/unit/domain/interactions/test_content.py` (text parts order / duplicates) | **PASS for text**; mixed image order is G2 |
| INT-004 | `tests/unit/domain/interactions/test_role.py`, `test_message.py` | **PASS** |
| INT-005 | `tests/unit/domain/interactions/test_content.py`, `test_message.py` | **PASS** |
| INT-006/007 | `test_role.py`, `test_message.py`, architecture guard | **PASS for Domain Core**; provider adapters later |
| INT-008 | `tests/unit/domain/interactions/test_text_content.py` | **PASS** |
| MOD-003 | `test_text_content.py` and acceptance | **PASS for text**; image later |
| MOD-005 | Strict typed representation; no converter in Domain Core | **PASS for current text core**; image tests later |

## 5. Qualification limits

1. `Conversation` implementation remains deferred under ADR-009; a Message works independently.
2. `ImageContent`, `MediaSourceRef`, `AC-007` and mixed content are L2.3.
3. `message_to_dict` / `message_from_dict`, strict JSON Interaction versioning and image round-trips are L2.4.
4. Other modalities and tool calling are deferred under ADR-013.
5. `main` was reported unprotected at G0. A successful PR and integrated CI are evidence of these particular commits, not a repository-wide guarantee for future changes.
6. No independent GitHub approval is claimed; the repo owner authorized proceeding with implementation in the conversation. The G1 verdict is a technical conclusion from integrated CI, not a separate human review signature.

## 6. Next work

Proceed to **L2.3 Multimodal Content** per ADR-011 and ADR-013: passive `MediaSourceRef`, immutable `ImageContent`, ordered text/image/text, and AC-007. Then implement independent Interaction JSON codec and cross-version qualification in L2.4.

## 7. Evidence preservation

The GO above references the already-tested `main` SHA `1fd7a476f0aa0b0040c0749ae36236fa24d6f8e6`. This documentation is archived by a separate PR. Archive integration creates a newer commit, so verify its own `main` CI and record final SHA and workflow link in the archival PR comment. No future CI status is predicted here.
