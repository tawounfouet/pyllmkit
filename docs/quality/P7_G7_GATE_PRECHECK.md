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

- [x] PR HEAD exact SHA CI succeeded in the recorded PR workflow.
- [x] Python 3.11, 3.12, 3.13, Ruff, mypy strict, wheel/sdist and examples pass.
- [x] New L7.7 test suite passes, including 6 x sync cancellation, 6 x async
  cancellation, premature EOF, and asynchronous cancellation during HTTP I/O.
- [x] Branch coverage gate for `streaming_resilience` >=95%.
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

## Gate decision - integrated engineering qualification (2026-11-06)

**GO for offline code integration and further development; NO-GO for live
production or release.** The owner explicitly authorized merging the
full #70-#79 stack despite the absence of independent GitHub reviews.
The resulting source baseline is `main@4633eba36`, with the three Python
CI jobs on the main push passing. Independent approval, branch protection
and live security qualification remain outstanding.

The integrated L7.6 coverage gate initially printed below-threshold
results even though GitHub marked its jobs successful; the follow-up
[#80](https://github.com/tawounfouet/pyllmkit/pull/80) explicitly
includes L7.7 resilience tests in the L7.6 coverage run, yielding
90.87% on Python 3.11-3.13 without lowering the 90% threshold. L7.7
itself recorded 100% branch coverage and 47 focused tests.
See [P7_G8_INTEGRATED_GATE_REVIEW.md](P7_G8_INTEGRATED_GATE_REVIEW.md)
for full evidence, accepted integration exception and remaining NO-GO items.
