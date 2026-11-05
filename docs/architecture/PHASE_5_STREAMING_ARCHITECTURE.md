# PyLLMKit P5 - Streaming architecture contract

> Status: architecture proposal, P5-G0 awaiting main CI evidence.
> Baseline: c896cbf22bf7893f8a0eb722c9fc3db641ed624b. Installed package stays at 0.1.0a2; 0.1.0b1 is a target only.

## Architecture

    Python consumers (application, notebook, agents)
                |
       sync Iterator / async AsyncIterator
                |
       InferenceStream Protocol
                |
       typed StreamEvent values
                |
       pure StreamReducer -> immutable StreamState
                |
       strict Streaming JSON v1 codec

Reuse M3 InferenceRunId, Usage and FinishReason and M4 ToolCallId, ToolCall and ToolArguments. The dependency direction runs from optional adapters to domain, never from domain to SDKs. No provider adapter or actual tool execution is part of M5.

## Event grammar

ResponseStarted, TextDelta, ToolCallStarted, ToolCallDelta, ToolCallCompleted, UsageUpdated, ResponseCompleted, ResponseFailed and ResponseCancelled. ToolCallDelta is the canonical name; no competing ToolArgumentDelta semantics.

Every event has run_id: InferenceRunId and sequence: exact int. First is ResponseStarted at 0; next must be previous+1. Wrong-run, gap, duplicate, out-of-order, missing-start and any post-terminal event fail deterministically.

Lifecycle: CREATED -> STARTED -> COMPLETED | FAILED | CANCELLED. Exhaustion before a terminal is INCOMPLETE, not successful. Partial outputs survive error and cancellation without inventing final inference responses.

## Reassembly

TextDelta is exact text without normalization. Each call ID has an independent raw-arguments buffer; ToolCallCompleted creates descriptive M4 ToolCall with parsed absent, not a ToolResult. StreamReducer does not parse JSON strings, execute tools or infer structured VALID. Snapshots UsageUpdated never fabricate token counts.

## Interfaces, resources, serialization

Separate stream(request) -> Iterator and astream(request) -> AsyncIterator protocols; producer controls close/aclose. Pull delivery only, no transport backpressure guarantee. Initial limits: 100000 events, 8 MiB UTF-8 text, 128 tool calls and 1 MiB UTF-8 raw per tool call.

Streaming JSON v1: exact schema_version 1, object_type stream_event, kind, run_id, sequence, payload, strict keys and no unknown variants. JSON text parsing and network frames are external. Model, Interaction, Inference and Tooling JSON v1 stay untouched.

## Delivery gates

P5-G0 design then L5.1 events, L5.2 ordering, L5.3 tool deltas, L5.4 sync/async, L5.5 serialization, L5.6 quality. Each has a distinct branch/PR and passing CI on merged main SHA before being labelled GO. M5 review and publication are separate. Existing reservations: issue #22 branch protection, #35 release authorization, #36 provider boundary.
