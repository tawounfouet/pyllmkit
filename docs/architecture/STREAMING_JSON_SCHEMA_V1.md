# Streaming JSON v1 - independent strict mapping schema

> PyLLMKit P5 L5.5, ADR-036. The codec maps objects to JSON-compatible dictionaries. It does not parse JSON text, SSE frames, provider payloads or transport bytes.

## Event envelope

Every StreamEvent is represented exactly by the keys schema_version, object_type, kind, run_id, sequence and payload. schema_version is exact int 1 (boolean 1 is rejected); object_type is stream_event; kind is a closed snake_case discriminant. Unknown, extra or missing keys are rejected at every level.

## Kind-specific payloads

| kind | required payload keys |
|---|---|
| response_started | none |
| text_delta | delta (string, exactly preserved) |
| tool_call_started | call_id, tool_name |
| tool_call_delta | call_id, delta (raw opaque text) |
| tool_call_completed | call_id |
| usage_updated | usage, is_final |
| response_completed | finish_reason |
| response_failed | reason_code |
| response_cancelled | reason_code |

usage contains all five M3 Usage fields with null distinct from zero. finish_reason is null or object code and native_reason (null allowed). Provider-native strings and fragments are never parsed to validate schema or invent a ToolResult. Object conversion only, not JSON text processing.

## Validated trace envelope

schema_version, object_type=stream_trace, run_id, events (list of event envelopes), observed_status. All keys required; unknown keys forbidden. Encoder and decoder replay ordered events through the deterministic reducer. Claimed terminality must equal replay-observed terminality (completed, failed, cancelled or incomplete), so a truncated stream cannot be mislabeled successful.

The APIs are event_to_dict, event_from_dict, stream_to_dict and stream_from_dict from pyllmkit.domain.streaming; examples may use json.dumps/json.loads outside the core. M1-M4 v1 codecs are not modified.

## Security and future boundaries

Strict validation of unexpected fields/types, duplicate positions, run mismatch, missing start, terminality and per-event budgets is performed before accepting values. A JSON text parser at a future boundary must separately reject duplicate object keys and enforce transport quotas. Do not claim exactly-once network delivery, safe deserialization of arbitrary huge JSON documents or an external provider integration.
