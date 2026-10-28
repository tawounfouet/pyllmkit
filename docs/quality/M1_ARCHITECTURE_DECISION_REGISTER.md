# M1 - Architecture Decision Register

**Updated:** 2026-10-28
**Status:** ADR-001 .. ADR-007 **ACCEPTED FOR PHASE 1 ALPHA** as project decisions under the owner's explicit instruction to complete M1.
**Evidence:** `docs/architecture/PHASE_1_PUBLIC_API_AND_CODECS.md`, code/tests and `LICENSE`.
**Disclosure:** This records an authorized engineering decision, not an independent human/legal review signature.

| ADR | Decision adopted for 0.1.0a1 | Tests/contract | State |
|---|---|---|---|
| ADR-001 | Typed ModelId / ModelArtifactId, preserve original nonblank value | Model identifier tests | ACCEPTED |
| ADR-002 | Immutable VO and Entity snapshots; identity equality; unhashable Entities | L1.1 tests | ACCEPTED |
| ADR-003 | Four SupportLevels; unknown represented by None | L1.2 tests | ACCEPTED |
| ADR-004 | ModelArtifact external reference, no mandatory artifact; strict frozen v1 codec with one-way historical read compatibility | Serializer, schema acceptance | ACCEPTED |
| ADR-005 | Python >=3.11, stdlib-only runtime, `pyllmkit.domain` and subpackages supported as public alpha imports | Root API tests | ACCEPTED |
| ADR-006 | Capability != Modality, directional content, effective support resolver deferred | L1.2 + TEST-MOD02 | ACCEPTED |
| ADR-007 | MIT license and no publication before separate release authorization | LICENSE + package metadata | ACCEPTED |

## Explicitly resolved findings

1. **Codec:** older development-time schema-v1 data are readable by the new decoder. An old strict v1 decoder may not read the new writer's additional fields; no false bidirectional compatibility claim. Future incompatible schema changes require version change and migration.
2. **Public imports:** root domain imports now re-export explicit classes and are tested; direct subpackage imports remain supported.
3. **Artifact referencing:** typed `model_id` is enforced, but persistence referential integrity is deferred to later repositories/registries.
4. **Capability resolution:** collections fail on conflicting declarations; `EffectiveCapabilitySet` is deferred and not simulated.
5. **License:** MIT selected as a default for this alpha; the repository owner may choose a different license *before any externally distributed release*, subject to compatibility/ownership review.

## Governance trail

- Project instruction: user asked to carry M1 through to validation, 2026-10-28.
- Implementation authority: technical design choices adopted within the scope of this delegated task; independent reviewer sign-off is not claimed.
- **G0 outcome:** architecture decisions adopted for alpha, subject to passing branch CI and integrated main CI.
- **M1:** still requires all stacked PR integrations and exact-SHA final checks; passing G0 alone is not M1.
