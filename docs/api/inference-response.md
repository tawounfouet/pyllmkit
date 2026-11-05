# PyLLMKit - Inference Response Domain API (L3.2)

> Scope (2026-11-05): **P3-G2 GO technique avec reserves**, code integre via [PR #25](https://github.com/tawounfouet/pyllmkit/pull/25), [main SHA 783aa438](https://github.com/tawounfouet/pyllmkit/commit/783aa4381dc05a4b9bc431faab282f2bbe37d38d), [CI #42039312011 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42039312011) (545 tests / 94 %, Python 3.11; 3 versions). [PV G2](../quality/P3_G2_GATE_REVIEW.md). Package 0.1.0a2 unpublished; a3 not released.
> Based on accepted ADR-014, ADR-017, ADR-018; preserves P3-G0 and P3-G1 contracts.
> Domain data only: no SDK, provider I/O, streaming, Run lifecycle or JSON Inference v1 codec.

## Value Objects

- `InferenceRunId(value: str)`: caller-provided nonblank opaque identity, immutable; no auto UUID. The same type will be used by the Run aggregate in L3.3.
- `InferenceOutput`: conceptual output family, represented in L3.2 as a **type alias** to the sole concrete subtype `TextOutput`, not an instantiable abstract base class.
- `TextOutput(text: str)`: exact immutable Unicode text, including `""`. `kind == "text"`. The output text is omitted from its default `repr` to reduce accidental logging.
- `FinishReasonCode`: STOP, LENGTH, TOOL_CALL, CONTENT_FILTER, CANCELLED, ERROR, UNKNOWN. A reason is **not** a RunState; TOOL_CALL does not execute any tool.
- `FinishReason(code, native_reason=None)`: normalized Enum plus native reason, which is preserved exactly if given. `None` for the entire finish_reason means **no reason provided**; UNKNOWN is never silently converted to STOP. Native value is hidden from `repr`.
- `Usage`: five optional nonnegative exact integer counts: `input_tokens`, `output_tokens`, `total_tokens`, `reasoning_tokens`, `cached_input_tokens`. Each defaults to `None`. Zero is a valid observation, not a replacement for missing data. No total is inferred and no consistency between independently reported metrics is invented.
- `InferenceResponse(run_id, output, finish_reason=None, usage=None)`: immutable Value Object. Requires typed RunId and `TextOutput`, carries no provider-native `raw` or metadata. Does **not** imply a completed Run; L3.3 later checks response.run_id against its RunId.

If a provider reports no Usage at all, pass `usage=None`; a standalone `Usage()` is structurally valid but conveys no observed counters. Pricing, Cost, tool execution and external invocation are not part of this contract.

## Offline example

```python
from pyllmkit.domain import (
    FinishReason, FinishReasonCode, InferenceResponse,
    InferenceRunId, TextOutput, Usage,
)

response = InferenceResponse(
    InferenceRunId("run-001"),
    TextOutput("Bonjour !"),
    FinishReason(FinishReasonCode.UNKNOWN, "vendor_specific_code"),
    Usage(input_tokens=8, output_tokens=0),
)
assert response.output.text == "Bonjour !"
assert response.usage is not None and response.usage.total_tokens is None
```

## Acceptance traceability

| Scenario | Contract |
|---|---|
| P3-AC-008 | TextOutput + Response constructed offline |
| P3-AC-009 | UNKNOWN retains native, never STOP |
| P3-AC-010 | Missing Usage remains `None` |
| P3-AC-011 | Partial Usage never invents a total |
| P3-AC-012 | Negative/boolean/float counters refused |
| P3-AC-013 | Usage distinct from Pricing / Cost |

Run transitions are deferred to L3.3, and JSON round-trips to L3.4. Passing L3.2 tests is not a release or completion of Phase 3.
