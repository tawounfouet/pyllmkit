# P7-G7 - Resilience, timeouts and cancellation gate

## Scope and dependencies

- **Lot**: L7.7, stacked on PR #78 (P7-G6).
- **Branch**: `p7/l77-resilience-timeouts-cancellation`.
- **Scope**: provider-neutral session cancellation, strict terminal semantics,
  transport deadline checks and fail-closed real sync streaming.
- **Out of scope**: retry policy beyond one attempt, automatic backoff,
  failover, remote provider cancellation, cloud budget authorization.
- **No real provider or Ollama network smoke tests**.

## Evidence required

- [ ] PR HEAD exact SHA CI succeeds in push and pull_request workflows.
- [ ] Python 3.11, 3.12, 3.13, Ruff, mypy strict, wheel/sdist and examples pass.
- [ ] New L7.7 test suite passes, including 6 x sync cancellation, 6 x async
  cancellation, premature EOF, and asynchronous cancellation during HTTP I/O.
- [ ] Branch coverage gate for `streaming_resilience` >=85%.
- [ ] Independent technical reviewer validates M5 protocol compatibility,
  RunId consistency, terminality and no stream replay.
- [ ] Independent security reviewer assesses timeout assumptions and safe
  transport termination.
- [ ] Upstream gates P7-G1..G6 are independently reviewed, then merged in order.
- [ ] main protection and policy issues #22, #35, #36 are resolved.

## Security evidence and limits

- All tests use fake adapters or HTTPX MockTransport; no genuine provider
  credentials or billable invocations.
- Forcing a sync socket with no injected deterministic transport fails with
  `sync_stream_deadline_not_enforceable` before credential retrieval/network.
- Cooperative local cancellation produces `ResponseCancelled`, not
  `ResponseCompleted`, and closes iterators when next resumed.
- Async task cancellation remains external `CancelledError` with cleanup.
- Async hard deadline exercises trickle under a deterministic local transport.
- Sync monotonic checks are **not** a general-purpose hard deadline:
  an active blocking call cannot be preempted using this mechanism.
- Neither async task cancellation nor cooperative flags guarantee remote
  inference termination, billing cessation or provider-side release.
- DNS/peer-IP/TLS runtime controls, retention and budgets remain NO-GO for live.

## Gate decision

**PENDING** until CI HEAD and independent reviews are recorded.

A CI-green code branch permits independent review, not merge or live execution.
