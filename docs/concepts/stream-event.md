# StreamEvent - Phase 5 L5.1

A StreamEvent is an immutable, run-correlated value representing progress of an inference, not a durable DomainEvent and not a provider frame. Import canonical types from pyllmkit.domain.streaming.

Each event is explicitly constructed with run_id: InferenceRunId and sequence: exact nonnegative int. ResponseStarted, TextDelta, ToolCallStarted, ToolCallDelta, ToolCallCompleted, UsageUpdated, ResponseCompleted, ResponseFailed and ResponseCancelled have distinct kinds. Content strings are excluded from repr and error messages.

L5.1 defines **event vocabulary only**. It does not validate a stream's ordering, reduce text or assemble tools; these operations belong to L5.2 and L5.3. It does not contact a provider, execute a tool or imply a final response. See ADR-030..038 and example 18_stream_text_events.py.
