# PyLLMKit - Inference JSON v1 contract (L3.4)

> **Status:** implementation candidate for P3-G4 (not yet qualified until main CI and gate report).
> **Authority:** ADR-020 ACCEPTED at P3-G0, after P3-G1, G2 and G3.
> **Scope:** JSON-compatible domain dictionaries. There is no LLM wire protocol, HTTP, JSON streaming, provider SDK or network I/O.

## Independent schema

`INFERENCE_SCHEMA_VERSION = 1`. This version does not change Model JSON v1 or Interaction JSON v1.

| Entry point | Exact `object_type` | Mandatory canonical fields |
|---|---|---|
| `request_to_dict` / `request_from_dict` | `inference_request` | `schema_version`, `object_type`, `target`, `messages`, `generation_config` |
| `response_to_dict` / `response_from_dict` | `inference_response` | `schema_version`, `object_type`, `run_id`, `output`, `finish_reason`, `usage` |
| `run_to_dict` / `run_from_dict` | `inference_run` | `schema_version`, `object_type`, `run_id`, `request`, `attempt`, `state`, `started_at`, `streaming_started_at`, `finished_at`, `response`, `failure`, `cancellation_reason_code` |

All canonical keys are **mandatory**, including those with a JSON `null` value. Unknown or missing keys are rejected, including nested objects. No migration, coercion, default injection or silent field removal occurs.

## Payload details

- Request target: exactly `{"kind": "model|deployment|endpoint", "value": "opaque-id"}`. The `kind` is one of three literal strings, not the combined phrase. The value is an opaque typed identifier: **no network resolution**.
- Request messages: nonempty array of **complete Interaction JSON v1 message envelopes**. Message/part order and duplicates are retained. Nested ImageContent carries a MediaSourceRef without fetching media.
- Non-null `generation_config`: all eight optional fields present: `temperature`, `top_p`, `top_k`, `max_output_tokens`, `seed`, `stop_sequences`, `presence_penalty`, `frequency_penalty`. `stop_sequences` is JSON `null` or an array (empty allowed).
- L3.1 strict float policy applies unchanged. `temperature=0.0` is a JSON float; integer `0` and boolean `false` are **invalid** for decimal configuration fields.
- Response output: `{"kind": "text", "text": "..."}` only. Empty `text` is valid. No structured/tool output or future extension is guessed.
- Response `finish_reason`: `null` or object with exactly `code` and `native_reason` (which may be `null`). `UNKNOWN` is a real code, distinct from absence and from `STOP`. The native value is preserved without mapping to any provider API.
- Response `usage`: `null` or all five counter keys present, each a nonnegative exact int or `null`. No total is inferred or corrected. Usage is **not** pricing or cost.
- Run snapshot: all fields present. CREATED, RUNNING, STREAMING, COMPLETED, FAILED, CANCELLED are validated using the L3.3 constructor; incoherent timestamps, payloads or RunId mismatches are rejected.
- Failure `{"code": "normalized_code"}` only; it never contains provider error dumps or stack traces. Cancellation reason is nullable and only allowed in CANCELLED.

Dates use timezone-aware ISO 8601 timestamps with an explicit offset. The encoder converts each observed instant to UTC, e.g. `2026-11-05T10:00:00+00:00`. The decoder returns a timezone-aware datetime representing the same instant; the original timezone *name* is not retained. No `datetime.now()` is read.

## Round-trip example

```python
import json

from pyllmkit.domain import (
    Content, GenerationConfig, InferenceRequest, Message, ModelId,
    ModelTarget, Role, TextContent, request_from_dict, request_to_dict,
)

request = InferenceRequest(
    ModelTarget(ModelId("example/model")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
    GenerationConfig(temperature=0.0),
)
payload = request_to_dict(request)
json_text = json.dumps(payload, allow_nan=False)
restored = request_from_dict(json.loads(json_text))
assert restored == request
```

Additional examples are in `examples/11_round_trip_inference_json.py` and the L3.4 tests.

## Strictness and boundary limitations

- The public functions operate on **JSON-style dict objects**. They are type-annotated with `Mapping[str, object]` for consistency with existing codecs, but the current Interaction v1 decoder accepts concrete dicts only. Generic MappingProxyType objects are not promised (see open PIR2-03, issue #20).
- `json.dumps` and `json.loads` are **the caller's responsibility**. Standard `json.loads` does **not detect duplicate keys** and, without caller policy, may accept nonstandard `NaN`/Infinity literals. L3.4 cannot recover keys that a parser already discarded.
- Domain decoders reject unexpected JSON-like object types, unknown fields/variants, wrong number types (including bool-as-int), non-finite configuration numbers, naive or incoherent timestamps, unknown nested ContentParts and mismatched RunIds.
- Values from malformed nested Interaction v1 structures are not echoed in Inference decoding exceptions. This is not a blanket logging-redaction framework; integrations must avoid logging raw untrusted data.
- The codec does not claim endpoint availability, actual streaming, token pricing, tool execution, provider compatibility or remote execution.

## Acceptance and evidence

P3-AC-021 (Request round-trip), 022 (Response round-trip), 023 (unknown schema/fields), 024 (unchanged Model/Interaction v1), 025 (offline/no credentials), 026 (clean wheel/sdist imports), 027 (sanitized errors), and 028 (unknown nested content part refusal) are covered by dedicated acceptance and regression tests.

Round-trip snapshots of **all six Run states** and strict invalid-state checks are additional explicit G4 evidence. P3-G4 must not be marked GO before a verified **main SHA CI**, and its verdict does not authorize tag, release or PyPI.
