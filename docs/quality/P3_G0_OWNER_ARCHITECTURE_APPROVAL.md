# PyLLMKit - P3-G0 Owner Architecture Approval

> **Date:** 2026-11-05
> **Authority:** Project owner explicit instruction in PyLLMKit conversation: "Pythos Go donc pour : La prochaine transition est donc P3-G0 : adoption des contrats, suivie d'une intégration contrôlée, d'une CI sur main et du procès-verbal de qualification."
> **Decision:** **ACCEPTED** for architecture contracts ADR-014..ADR-021, with the review recommendations and explicit choices below.
> **Nature of authority:** owner authorization to adopt, integrate and qualify; this is not a third-party GitHub APPROVED review or security audit.
> **Implementation status:** none of these a3 domain primitives are implemented by this architecture decision.
> **Release / publication:** not authorized.

## Owner decisions D-01 to D-10

| Decision | Adopted rule |
|---|---|
| D-01 | ModelTarget, DeploymentTarget and EndpointTarget remain three separate, typed, unresolved target variants. |
| D-02 | a3 chat Request has 1..* immutable ordered Message values. Broader domain patterns stay future scope. |
| D-03 | InferenceRun is an Aggregate Root with immutable snapshots; identity equality is based on RunId, while state comparison is explicit. |
| D-04 | InferenceFailure carries normalized code only; terminal states use finished_at, with optional cancellation_reason_code. |
| D-05 | GenerationConfig uses strict **finite float only** for decimal parameters and exact int excluding bool for integer parameters, with None for omission. |
| D-06 | TextOutput permits empty text; absent finish_reason is None, unknown native reason yields UNKNOWN with source value retained. |
| D-07 | Usage stores observed optional nonnegative counters, no implied total, pricing or cost calculation. |
| D-08 | Inference JSON v1 uses independent namespace, strict Request/Response/Run envelopes and valid snapshots for all six states. |
| D-09 | **ADR-021 Option A accepted**: minimal pure evaluator on explicit caller-supplied support snapshot, to satisfy P3-AC-007; no public executable InferencePort or provider adapter. |
| D-10 | Domain events remain conceptual and there is no real streaming, HTTP invocation, orchestrator, scheduler or event bus in a3. |

## Coverage of review findings

- F-01: InferenceFailure and terminal finished_at are accepted in ADR-019/020.
- F-02: Run snapshot equality versus state comparison is defined in ADR-019.
- F-03: ADR-021 Option A is accepted; P3-AC-007 remains **REQUIRED**, not deferred and not yet passed.
- F-04: strict float-only inputs are intentionally accepted despite ergonomics tradeoff; tests will explicitly reject integer 0 for temperature.

## Accepted preparation scope

- **51 tasks** in the phase plan: implementation backlog, not done.
- **30 acceptance scenarios**: baseline test catalog for engineering qualification, not yet passed.
- **Gates P3-G1..G5 and M3**: remain future decisions based on executable evidence.
- PIR2-01/02/03 are isolated in [issue #20](https://github.com/tawounfouet/pyllmkit/issues/20), **not resolved**.
- M1/M2 behavior, public imports and serialization v1 must not be broken.

## G0 evidence chain

1. Contradictory design review: [P3_G0_ARCHITECTURE_REVIEW.md](P3_G0_ARCHITECTURE_REVIEW.md).
2. Owner explicit instruction: 2026-11-05 PyLLMKit conversation (documented here, not represented as a GitHub review).
3. Owner-approved decisions: ADR-014..021 updated on PR [#19](https://github.com/tawounfouet/pyllmkit/pull/19).
4. **Pending at time of this record:** qualifying PR CI on final head, intentional merge, exact post-integration main SHA and CI.
5. Formal P3-G0 GO/NO-GO must be published in a separate gate record after evidence is collected, not inferred from this document.

No signed release, tag, wheel publication, PyPI upload or provider-invocation capability is approved by this record.
