# PyLLMKit v0.3.0 - S5 Native Stream Lifecycle Conformance

> Date: 2026-11-06
> Status: **S5 PARTIAL ENGINEERING GO; G5 INDEPENDENT REVIEW PENDING**
> Base: S4 history/Usage/FinishReason PR #93
> Issue: #87
> Test evidence: `67ec571ef930f59154a4dbd625ca418691217395`
> No provider live connections, tags, releases or version changes.

## Scope

S5 qualifies the **observable lifecycle** of each of the six native
streaming adapters in both sync and async modes through an injected
`httpx.MockTransport` and tracked fake byte streams.

This tranche does not claim remote cancellation. Cancellation is a
cooperative local consumption signal. External asyncio task cancellation
must propagate to the caller, close the underlying stream and not become
a fabricated provider `ResponseCancelled` event. The existing
production **synchronous real streaming socket** refusal
`sync_stream_deadline_not_enforceable` is preserved.

## Implemented tests

| Scenario | Dimensions | Count | Contract oracle |
|---|---|---:|---|
| Mid-stream cooperative cancel | 6 providers x sync/async | 12 | Started, delta, one Cancelled, socket closed |
| One-shot session cannot be replayed | 6 providers x sync/async | 12 | Reject second iterator without opening transport |
| External task cancel during blocked async read | 6 providers | 6 | `CancelledError` propagates, async stream closed |
| Cancel after completed session | 6 providers x sync/async | 12 | One Completed, no second terminal |
| **Total** | | **42** | Native SSE/NDJSON, mock-only |

Fixtures: `tests/conformance/stream_fixtures.py` synthetic wire
profiles `v030-s2-stream-v1`. Each native request passes through
the actual `NativeProviderStreamingAdapter`, not a FakeInferenceAdapter.
Transport streams expose a `closed` flag asserted after early
cancellation. The suite also asserts exactly one mock request for an
already-started session and **zero** for a never-consumed iterator.

Files:
- `tests/conformance/test_v030_s5_stream_lifecycle.py`
- `tools/v030_conformance_report.py` with mandatory S5 scenario minima.

## Verified results

- [GitHub Actions #42224645155](https://github.com/tawounfouet/pyllmkit/actions/runs/42224645155)
- Implementation SHA:
  `67ec571ef930f59154a4dbd625ca418691217395`
- Python 3.11, 3.12, 3.13: all **SUCCESS**
- General suite **2,644 tests passed per version**
- Conformance reporter **PASS, 680 cases per version**
- Three nonempty evidence artifacts (v030-conformance-3.11/3.12/3.13)
- Ruff, strict typing, historical P7 gates and wheel/sdist smoke successful

This is an offline deterministic proof at the exact tested SHA, not
a remote live provider certification or an observation of billing stop.

## Remaining G5 work

- [x] Cancel after first delta, 6 native providers and two modes
- [x] Resource closure for both mock sync and async streams
- [x] External async `Task.cancel()` propagation on blocked read
- [x] Terminal uniqueness after completion
- [x] Single-session replay prevention and zero transport attempts
- [ ] Independent review of provider-specific SSE/NDJSON framing and cleanup
- [ ] Egress peer IP/DNS/TLS hardening and live canaries (#36/#81)
- [ ] Verify production hard deadlines, especially synchronous streaming
- [ ] Robust active session cancellation under non-cooperative real HTTP peers
- [ ] Full gate G5 signed off and integrated S8 GO/NO-GO

**Verdict: GO for the completed offline lifecycle slice; PENDING for
full S5-G5, production, real provider compatibility and release.**
