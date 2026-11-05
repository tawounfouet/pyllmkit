# ADR-012 - Independent versioned Interaction JSON codec

- **Status:** ACCEPTED for Phase 2 design (P2-BOOT, 2026-11-05). Implementation and M2 qualification remain pending.
> **Post-implementation clarification (2026-11-05):** This line records the historical P2-BOOT decision, not the current implementation state. M2's source candidate was subsequently implemented and qualified on [`main@560d3a46`](https://github.com/tawounfouet/pyllmkit/commit/560d3a46c74cecebdf6a55301b2b8ca4e34331d4), [CI #42015825424](https://github.com/tawounfouet/pyllmkit/actions/runs/42015825424) PASS, [M2_GATE_REVIEW](../quality/M2_GATE_REVIEW.md). Package metadata `0.1.0a2` remained unpublished. This note does not revise the 2026-11-05 owner architecture decision.

- **Authorization:** Explicit review and approval by the repository project owner in the PyLLMKit project conversation on 2026-11-05. This is an owner decision, not a GitHub review submission or independent architecture audit.
- **Decision effective date:** 2026-11-05.
- **Context:** Interaction VOs need deterministic serialization without reusing the frozen Model schema v1 or adopting a provider API wire format.
- **Sources:** ADR-004; Phase 2 plan section 5; specifications 07 (INT-003/007), 05, 06.

## Decision
1. Create `pyllmkit.domain.interactions.serialization` independent from `pyllmkit.domain.models.serialization`. Expose explicit `message_to_dict` and `message_from_dict` functions, with a separate `INTERACTION_SCHEMA_VERSION = 1` constant.
2. Canonical top-level shape:
   ```json
   {
     "schema_version": 1,
     "object_type": "message",
     "role": "user",
     "content": {"parts": [
       {"kind": "text", "text": "Regarde cette image"},
       {"kind": "image", "source": {"kind": "asset", "value": "image-123"}}
     ]}
   }
   ```
3. Strictly validate known keys, object types, version (exact JSON integer `1`, not boolean), role and every nested kind; reject unknown keys, unknown types, missing fields and malformed payloads with `DomainValidationError`. No silent dropping or coercion.
4. Preserve ordering, duplicate content parts, exact text bytes after UTF-8 JSON round trip, media reference values and the canonical Role. Do not include provider-native JSON.
5. Initial schema v1 excludes Message IDs, timestamps, name/metadata and all unknown content kinds. Any incompatible public schema evolution requires a new version plus migration policy.
6. Do not modify `model_to_dict`, `model_from_dict`, `artifact_to_dict`, `artifact_from_dict`, or Model schema v1 output.
7. Model codec v1 previously offered backward reading of earlier development snapshots, not guaranteed bidirectional compatibility; do not misstate that baseline.

## Alternatives
- Reuse the Model codec/version namespace: rejected, independent domains and schemas.
- Emit OpenAI/Anthropic message wire payloads: rejected, provider coupling.
- Ignore unknown JSON keys for convenience: rejected, silent data loss.

## Consequences
- An explicit stable candidate for a2 without claiming this is a published external standard.
- New modalities later require versioned serialization design rather than opaque pass-through.
- No migration behavior is claimed until separately designed and tested.

## Acceptance Tests
- Text and image Message -> mapping -> JSON -> Message are equal by value.
- Order, duplicates, empty text and media reference survive round-trip.
- Invalid version, fields, role, type and media source fail deterministically.
- All M1 codec tests pass unchanged, including schema v1 behavior.

## Follow-ups
- L2.4: implement the codec and round-trip tests after types exist.
- M2: freeze actual emitted schema based on passing tests, with examples and changelog.
