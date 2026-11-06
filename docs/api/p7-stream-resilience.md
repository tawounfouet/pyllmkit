# P7 L7.7 - Streaming resilience, timeouts and cancellation

## Scope

PyLLMKit retains the M5 `StreamingPort.stream(request)` and
`AsyncStreamingPort.astream(request)` protocols, M5 `StreamEvent` types and
deterministic M5 reducer. L7.7 adds session-local cooperative cancellation,
strict terminal semantics and conservative network deadline behavior.

The provider-neutral `StreamingSession.cancel()` and
`AsyncStreamingSession.cancel()` mark only their own session for cancellation.
On the next pull, the wrapper emits M5 `ResponseCancelled(reason_code="user_cancelled")`
with a contiguous sequence, closes the underlying iterator and never emits
`ResponseCompleted`. This represents a **local** cancellation; it is not
evidence that the provider terminated a remote run or ceased billing.

The session may be consumed once only, preserving its `InferenceRunId`.
A prematurely exhausted adapter that did not emit a terminal event becomes
`ResponseFailed("provider_not_completed")` rather than an invented success.
An already delivered terminal event cannot be changed by later cancellation.

### Synchronous safety boundary

HTTPX sync read timeouts protect read phases, **not** the absolute wall-clock
duration against a trickling peer or indefinite blocked reads. L7.7 adds
monotonic per-line elapsed-time checks for deterministic injected transports,
but explicitly forbids real synchronous streaming sockets with
`ResponseFailed("sync_stream_deadline_not_enforceable")` until a reviewed
hard-stop execution boundary is available. The application-level sync port
continues to work offline and retains its original signature. This deliberate
restriction protects the NO-GO for a non-enforceable live sync deadline.

### Asynchronous safety boundary

The existing `asyncio.timeout(timeout)` in the native async transport is a
wall-clock bound during active consumption. An external `asyncio.Task.cancel()`
propagates `CancelledError`; it is **not** translated into
`ResponseCompleted` or a claim of remote cancellation. Nested HTTPX async
context managers and generator `finally` blocks close the local response
and transport when cancellation is propagated.

`AsyncStreamingSession.cancel()` is cooperative, checked at the next
consumer pull. It does not forcibly cancel an in-flight `anext()`; callers
that need prompt cancellation during a blocked read should cancel their
consumer task and explicitly close the async generator in a `finally`.

### Reliability policy

- One provider target, one native model alias, one logical RunId and one
  attempt. No automatic retries after partial content, fallback routing,
  response replay or duplicate billing.
- The canonical stream never fabricates usage, finish reasons or terminal
  provider events.
- Fatal provider and timeout errors remain sanitized codes without native
  HTTP bodies or credentials.
- Explicit `allow_live` opt-in remains necessary but **not sufficient** for
  production authorization.
- The current HTTPX MockTransport tests cannot prove DNS pinning, peer IP,
  real certificate negotiation or cloud account budget limits.

## Demonstration

```python
session = streaming_service.open_stream(request, support_snapshot)
iterator = iter(session)
first = next(iterator)
session.cancel()  # Local flag only, no remote API request to cancel.
remaining = list(iterator)  # ResponseCancelled with the same run_id.
```

For native asyncio tasks, always close an interrupted iterator:

```python
stream = aiter(async_session)
try:
    async for event in stream:
        ...
finally:
    await stream.aclose()
```

## Qualification

See `docs/quality/P7_G7_GATE_PRECHECK.md`.
No live provider calls, merges, releases or tags belong to this lot.
