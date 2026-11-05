# PyLLMKit - P3 L3.4 Inference JSON Codec & Quality - Implementation Summary

> Date: 2026-11-05
> Status: IMPLEMENTED ON FEATURE BRANCH, P3-G4 NOT YET QUALIFIED
> Architecture authority: ADR-020 (ACCEPTED by owner at P3-G0)
> Baseline: main `1e231d5cac7d7f33f394b4ea7e3cb2f86e948604` (P3-G3 GO)
> Version metadata: 0.1.0a2, untagged and unpublished
> Scope: strict JSON-compatible Python mapping, no HTTP/SDK/provider codec

## 1. Deliverables

- `src/pyllmkit/domain/inference/serialization.py`: standalone `INFERENCE_SCHEMA_VERSION = 1`, independent `request_to_dict`/`request_from_dict`, `response_to_dict`/`response_from_dict` and `run_to_dict`/`run_from_dict`.
- Public reexports from `pyllmkit.domain.inference` and `pyllmkit.domain`.
- `tests/acceptance/test_p3_l34_inference_json_v1.py`: P3-AC-021..028 and six run state round trips.
- `tests/unit/domain/inference/test_serialization_strict.py`: strict schema/field/date/type/enum/ID rejection tests.
- `examples/11_round_trip_inference_json.py`: runnable complete offline example on Request, Response and Run.
- `docs/api/inference-json-v1.md`: contract, schema, known parser limits and usages.
- CI updates: example 11, wheel/sdist clean smoke and architecture fitness expansion.

## 2. Architecture and invariants

1. Three distinct versioned envelope object types: `inference_request`, `inference_response`, `inference_run`.
2. All v1 fields present, including `null`, and all nested object keys exact. Unknown fields, omissions and unapproved variants cause `DomainValidationError`.
3. Interaction Message nested envelopes reuse existing **Interaction JSON v1** with order and duplicates retained, including media references with no fetching.
4. GenerationConfig strict exact finite float; stop sequences nullable vs empty list distinction; no auto defaults or coerced values.
5. TextOutput and FinishReason native values preserved; Usage partial totals never invented; bool rejected as int.
6. All six Run snapshots are reconstructed through the public aggregate constructor, requiring coherent timestamps, terminal payload exclusivity and a matching RunId.
7. Timestamps are UTC at serialization; decoder accepts timezone-aware ISO 8601 with explicit offset, returning equivalent UTC instant; no wall clock read.
8. Error messages do not echo unknown keys, nested prompt values, provider URL values or raw source errors.
9. Standard JSON text duplicate-key rejection remains **caller responsibility** (as ADR-020 states); these functions do not implement an HTTP/text parser.

## 3. Acceptance matrix

| Scenario | Test | Required evidence |
|---|---|---|
| P3-AC-021 | request JSON round-trip | Value equality, content order, config |
| P3-AC-022 | response JSON round-trip | Usage and UNKNOWN/native reason |
| P3-AC-023 | unknown version/fields | Domain rejection, no drop |
| P3-AC-024 | Model/Interaction v1 unchanged | Regression and independent version |
| P3-AC-025 | offline no credential I/O | Offline run codec example |
| P3-AC-026 | clean wheel/sdist exports | CI smoke |
| P3-AC-027 | sensitive data in errors | Sanitized failures, no raw value echo |
| P3-AC-028 | unknown content part | Fail closed via Interaction v1 |
| Extra | 6 Run states | Pure JSON round-trip + forbidden-state checks |

## 4. Gate status

G4 stays **PENDING** until final PR head CI green, intentional merge, exact integrated main SHA CI, and a separately archived gate report. P3-G5, M3 and release remain independent future approvals. The M2 debt [#20](https://github.com/tawounfouet/pyllmkit/issues/20) and main protection [#22](https://github.com/tawounfouet/pyllmkit/issues/22) remain open.

No tag, version bump, GitHub Release or PyPI upload is in scope.
