# M1 - Architecture Decision Register

**Review date:** 2026-10-28
**Approval:** NOT GRANTED. All ADRs are still formally **PROPOSED**.
**Source:** specifications 02 / 03 / 05 / 06 / 07 and `01_PYLLMKIT_PHASE_1_IMPLEMENTATION_PLAN.md`.

This register is a technical **recommendation**, not an invented stakeholder approval.

| ADR | Technical review | Recommended disposition | Approval |
|---|---|---|---|
| ADR-001 Typed IDs | `ModelId` and `ModelArtifactId` are distinct frozen VOs; errors on blank IDs; no provider-specific canonical IDs | Accept for alpha, document normalization/case conventions explicitly | **PENDING** |
| ADR-002 Entity identity | `Model` and `ModelArtifact` compare by typed ID; snapshots immutable and intentionally unhashable | Accept for alpha, reconsider aggregate mutation semantics before stable API | **PENDING** |
| ADR-003 UNKNOWN support | `SupportLevel` has 4 explicit values; absent declaration maps to `None`, not NATIVE/UNSUPPORTED | Accept for alpha; specify client semantics of `supports() == False` on unknown | **PENDING** |
| ADR-004 Artifact & schema | Artifacts reference logical model; model does not require artifact or deployment; strict schema-v1 JSON mapping | Accept for alpha **with compatibility clarification** below | **PENDING** |
| ADR-005 Dependencies/API | `src/` layout; no mandatory provider SDK; domain imports guarded; package public reexports under subpackages | Conditional accept: settle the intended root `pyllmkit.domain` API before documenting an import promise | **PENDING** |
| ADR-006 Capability/Modality | Extensible descriptors, constraints, directional modalities, no implicit effective capability resolver | Accept for alpha; distinguish declared support from later restrictive resolution | **PENDING** |

## Finding A - Schema compatibility is directional (ADR-004)

The L1.2 writer includes `capabilities` and `modalities` in the version-1 model mapping. The L1.2 reader tolerates older L1.1 documents that omitted them. But an **older strict L1.1 reader** rejects the additional keys written by L1.2 while schema_version remains 1.

This is **backward-read compatibility**, not bidirectional compatibility or full forward compatibility. Neither variant was externally published at the time of this review, so the final `0.1.0a1` codec can be frozen at version 1. Before publishing, approve a compatibility policy: schema revisions on additive fields vs optional field extensions, reserved extensions, and explicit migrations.

## Finding B - Root package facade is still intentionally undecided (ADR-005)

The implemented API is `from pyllmkit.domain.models import Model` and related subpackages; `pyllmkit.domain.__init__` is not currently a complete re-export facade. This is consistent with deferring the stable root API, but it must not be claimed that `from pyllmkit.domain import Model` works unless it is explicitly implemented and tested.

**Recommendation:** adopt subpackage-first exports for alpha, or implement a documented root facade with tests. Either choice must be captured in an approved ADR.

## Finding C - Ownership vs foreign-key reference (ADR-004)

A `ModelArtifact` enforces a typed `ModelId` reference, not the existence of a persisted `Model`. Referential existence cannot be enforced without a registry/repository, which is out of Phase 1 scope. This is not a failure of Domain primitives, but any later registry must enforce the relationship `MODEL-013` at write boundaries.

## Finding D - Effective support remains intentionally deferred (ADR-006)

`CapabilitySet.union/intersection` do not resolve conflicting provider/deployment capability declarations; they raise. Later `EffectiveCapabilitySet` must implement restrictive precedence, unknown treatment and emulation provenance. Do not call `CapabilitySet.intersection` an effective capability resolver.

## ADR approval protocol

1. Have the architecture owner review the six ADRs and record ACCEPTED / SUPERSEDED / REJECTED with dates and rationale.
2. Update any disputed Python public contract, tests and documentation *before* M1 approval.
3. For ADR-004 and ADR-005, formally adopt the alpha codec/API contract.
4. Only then update G0 in `M1_GATE_REVIEW.md`.

**No ADR status is changed by this review branch.**
