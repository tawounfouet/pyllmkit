# Stream reassembly - P5 L5.2

StreamReducer is a pure function, not an inference executor. The input StreamState and StreamEvent determine the new immutable StreamState. No network, JSON text parser or provider SDK is invoked.

Ordered stream events use 0-based contiguous sequence numbers for the same InferenceRunId. The first is ResponseStarted, and a successful end requires ResponseCompleted; ResponseFailed and ResponseCancelled remain distinct terminals. Any EOF without an explicit terminal is INCOMPLETE, including EOF before start. Terminal states reject all further events. Missing/duplicate/out-of-order and mixed runs yield deterministic, payload-free errors.

Text fragments live in a persistent immutable linked list: appending does not repeatedly rebuild the entire string, and state.text joins them on demand. Tool event identities and open/closed state are checked, but raw tool argument reassembly is scheduled for L5.3. UsageUpdated is a snapshot with explicit is_final, not an additive delta. There is no ToolResult or InferenceResponse synthesized by this reducer.

Bounded L5.2 profile: 100000 events, 8 MiB UTF-8 text and 128 tool calls. See ADR-031/032/034/038 and tests P5-AC-009..016.
