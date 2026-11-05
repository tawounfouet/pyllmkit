# PyLLMKit - P3 / L3.1 Implementation Summary

> **Date:** 2026-11-05
> **Milestone:** L3.1 - Inference Request Domain
> **Status:** IMPLEMENTED ON FEATURE BRANCH - **P3-G1 PENDING QUALIFICATION**
> **Target source version:** 0.1.0a3 (future alpha, **not published**). Repository metadata remains 0.1.0a2.
> **Architecture approval:** [P3-G0 Gate Review](P3_G0_GATE_REVIEW.md), ADR-014/015/016/021 (option A).
> **Feature PR:** [#23](https://github.com/tawounfouet/pyllmkit/pull/23).
> **Release and publishing:** explicitly out of scope.

## 1. Delivered domain primitives

| Module | Values / functions | Boundary |
|---|---|---|
| `inference/targets.py` | ModelTarget, DeploymentTarget, EndpointTarget and typed IDs | Passive identities; no Serving resolution |
| `inference/config.py` | GenerationConfig | Exact finite float, int excluding bool, optional/None, immutable tuple |
| `inference/request.py` | InferenceRequest | Immutable ordered 1..* M2 Message values, no Conversation or request ID |
| `inference/compatibility.py` | ParameterSupport, GenerationSupportSnapshot, ParameterAssessment, CompatibilityReport, evaluate_request_support, validate_request_support | Pure, caller-supplied support snapshot; UNKNOWN not NATIVE; UNSUPPORTED rejected |
| `inference/__init__.py` and domain root | Public imports | M1/M2 imports kept |
| `docs/api/inference-request.md` | Public contract documentation | Intention, not invocation |
| `examples/08_define_inference_request.py` | Runnable example | Offline only, invoked in CI |

## 2. Acceptance scenario mapping

| Acceptance | Implementation test | Expected proof |
|---|---|---|
| P3-AC-001 | `test_p3_ac001_create_model_request_with_text_message` | Typed text request |
| P3-AC-002 | `test_p3_ac002_preserve_mixed_content_and_order_without_vision_claim` | Text/image order, no effective support invented |
| P3-AC-003 | `test_p3_ac003_missing_target_rejected` | Explicit DomainValidationError |
| P3-AC-004 | `test_p3_ac004_non_finite_temperature_rejected` | NaN/Infinity rejected |
| P3-AC-005 | `test_p3_ac005_none_vs_zero_max_output_tokens` | Distinct absence vs invalid zero |
| P3-AC-006 | `test_p3_ac006_bool_rejected_for_integer_parameters` | No bool-as-int coercion |
| P3-AC-007 | `test_p3_ac007_explicit_unsupported_parameter_rejected_without_fallback` | Explicit snapshot with UNSUPPORTED, no fallback |

Unit tests also check strict Target types, immutable config, message ordering, mismatched support snapshots, unknown/partial/emulated support, invalid support reports, and negative cases. Architecture tests prevent known provider imports and verify domain root aliases.

## 3. Noteworthy semantics

1. `GenerationConfig.temperature=0.0` is valid; integer `0` is invalid by explicit P3-G0 ADR-016 decision.
2. An empty tuple `stop_sequences=()` is a **present value** distinct from `None`.
3. Compatibility is only evaluated against a **caller-provided snapshot for the exact typed target**. There is no provider discovery or runtime capability resolution.
4. If any explicit requested parameter is `UNSUPPORTED`, `validate_request_support` raises `DomainValidationError` with a fixed allowlisted parameter name. Unknown/partial/emulated support never becomes confirmed native.
5. If no parameters have been assessed, `is_compatible is None` and `is_confirmed_native is False`, never a fictitious positive result.
6. A request containing `ImageContent` represents intent but does not establish effective vision capability.
7. No external provider SDK, client, streaming, ToolCall/ToolResult, JSON Inference codec, Run/Response, event bus or I/O.

## 4. Qualification evidence and outstanding gates

- **Previously verified PR head `140e25776fbc76a7b387d617f3d51e40ab8b3b1b`**: CI [#42035719738](https://github.com/tawounfouet/pyllmkit/actions/runs/42035719738) SUCCESS on three Python versions. Python 3.11: 431 tests, 93% coverage.
- **Improved HEAD `fa52065323c890bc52ce979d5768b10f3afc8c9b`**: CI [#42036074674](https://github.com/tawounfouet/pyllmkit/actions/runs/42036074674) SUCCESS on three Python versions, Python 3.11: **432 passed, 93% coverage**, ruff/mypy green. Corrected empty-support semantics and enforced report invariants.
- **Current feature branch may move** for packaging smoke and this summary; **do not infer CI success for later SHAs**.
- **Before G1 GO**: final PR head CI green, voluntary merge, CI success on exact merged `main` SHA, independent gate report with evidence.
- Governance reservations remain: `main.protected=false` (issue [#22](https://github.com/tawounfouet/pyllmkit/issues/22)); M2 debt [#20](https://github.com/tawounfouet/pyllmkit/issues/20) open. These do not authorize publication.

**G1 is NOT yet GO in this implementation summary.**
