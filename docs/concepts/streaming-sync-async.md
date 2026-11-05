# Streaming synchronously and asynchronously - P5 L5.4

The vocabulary and reducer are identical across sync and async. InferenceStream and AsyncInferenceStream are separate structural protocols with a caller-supplied run_id, and StreamingPort / AsyncStreamingPort describe future adapters. No network, SDK, thread, transport or tool executor is supplied.

MemoryInferenceStream and MemoryAsyncInferenceStream are in-memory fixtures for offline experiments. consume_stream and consume_async_stream reduce ordered events with identical semantics, optional explicit max_events cutoff, and a faithful EOF state. An exhausted stream without ResponseCompleted/Failed/Cancelled is INCOMPLETE. A ResponseCancelled event is terminal but not successful. UsageUpdated snapshots carry partial Usage; missing token counts remain None.

On early cutoff, the caller owns the resource-bearing generator and must explicitly close/aclose it when appropriate; this consumer never falsely emits a completion event or promises network backpressure. The asynchronous port method returns AsyncIterator directly, so using it requires async for but not an initial await.

Example 20 runs in asyncio only at the example boundary. The domain imports no asyncio and has no provider dependencies. Tests P5-AC-025..032 cover parity, cancellation, incomplete usage, early close, limits and validation.
