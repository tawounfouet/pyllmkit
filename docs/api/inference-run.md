# PyLLMKit - Inference Run Domain API (L3.3)

> Scope (2026-11-05): **P3-G3 GO technique avec reserves**, [PR #27](https://github.com/tawounfouet/pyllmkit/pull/27) integrated on [main 361791ff](https://github.com/tawounfouet/pyllmkit/commit/361791ff546612e10b407874c54014b1c0e1ce86), [CI #42044787119 SUCCESS](https://github.com/tawounfouet/pyllmkit/actions/runs/42044787119): 679 tests/94% coverage, 3 Python versions. [Gate report](../quality/P3_G3_GATE_REVIEW.md).
> Architecture authority: ADR-014, ADR-019 (ACCEPTED at P3-G0).
> Runtime status: domain-only state machine, **not** an executor or an LLM client.
> Source package version: `0.1.0a2` until a separate 0.1.0a3 qualification and release decision.

## 1. Entity, identity and pure snapshots

`InferenceRun` is a domain **Entity / Aggregate Root**. It has exactly one `InferenceRequest`, an explicit `InferenceRunId` (introduced in L3.2), and an `attempt: int >= 1`. A retry or replay creates a *new* RunId, not a network retry.

Snapshots are frozen. Each transition creates a **new instance with the same identity**, leaving the previous state unchanged. Equality and hashing compare only RunId; therefore a CREATED snapshot and a COMPLETED snapshot with the same id compare equal. To test a transition, compare `state`, `started_at`, `streaming_started_at`, `finished_at`, `response` and `failure` explicitly. `same_identity_as` makes identity comparison explicit.

Neither the request, the output, the normalized failure nor the cancellation reason is included in the aggregate's default `repr`.

## 2. States and legal transitions

| From | Action | To | Preconditions |
|---|---|---|---|
| CREATED | `start(at)` | RUNNING | timezone-aware datetime supplied by caller |
| RUNNING | `begin_stream(at)` | STREAMING | at >= started_at; no actual streaming |
| RUNNING / STREAMING | `complete(response, at)` | COMPLETED | typed Response with same RunId; coherent time |
| RUNNING / STREAMING | `fail(failure, at)` | FAILED | typed InferenceFailure code; coherent time |
| RUNNING / STREAMING | `cancel(at, cancellation_reason_code=None)` | CANCELLED | time and optional normalized code |

No other transitions are legal. CREATED cannot directly fail/cancel/complete; COMPLETED, FAILED and CANCELLED are irreversible terminal states. A repeated action on the same terminal snapshot raises `DomainValidationError`.

**STREAMING is descriptive**. Calling `begin_stream` does not instantiate a stream, fetch chunks, emit a StreamEvent or invoke a provider.

## 3. Snapshot invariants

| State | started_at | streaming_started_at | finished_at | response | failure | cancellation_reason_code |
|---|---|---|---|---|---|---|
| CREATED | None | None | None | None | None | None |
| RUNNING | date | None | None | None | None | None |
| STREAMING | date | date | None | None | None | None |
| COMPLETED | date | date/None | date | REQUIRED / same id | None | None |
| FAILED | date | date/None | date | None | REQUIRED | None |
| CANCELLED | date | date/None | date | None | None | code/None |

Every non-null timestamp must be timezone aware, supplied explicitly; ordering `started_at <= streaming_started_at <= finished_at` is enforced where applicable. No `datetime.now()` or automatic UUID is used by the aggregate. Direct reconstruction of invalid snapshots is rejected, to prepare the strict JSON decoder in L3.4.

`InferenceFailure(code: str)` contains only a normalized snake_case code (e.g. `provider_unavailable`), never the provider exception or stack trace. Cancellation code follows the same normalized pattern and is optional. Both codes are excluded from default `repr`. Domain invalidity/transition errors use `DomainValidationError`, **not** a fabricated InferenceFailure.

## 4. Offline illustration

```python
from datetime import datetime, timezone

from pyllmkit.domain import (
    Content, InferenceRequest, InferenceResponse, InferenceRun,
    InferenceRunId, InferenceRunState, Message, ModelId,
    ModelTarget, Role, TextContent, TextOutput,
)

request = InferenceRequest(
    ModelTarget(ModelId("offline/llm")),
    (Message(Role.USER, Content((TextContent("Bonjour"),))),),
)
started = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
created = InferenceRun(InferenceRunId("run-1"), request)
running = created.start(started)
completed = running.complete(
    InferenceResponse(created.run_id, TextOutput("Bonjour !")), started
)
assert completed.state is InferenceRunState.COMPLETED
assert created.state is InferenceRunState.CREATED
assert created == completed  # same Entity identity
```

## 5. Traceability and deferred capabilities

- Tests `P3-AC-014..020` and `P3-AC-029` cover distinct runs, transitions, mismatch rejection, replay and explicit clock.
- Unit tests cover the legal transition matrix, forbidden edges, six state constructor invariants, equality, immutability, normalization and timestamps.
- `InferenceRunId` and `InferenceResponse` are reused from L3.2. No new provider-facing objects or SDKs are introduced.
- Domain events remain a **documented semantic catalog** (ADR-019), not an event publisher. No persistence, event bus, executor, HTTP, retry scheduler, real streaming or raw native provider error.
- `request_to_dict`, `run_to_dict`, `response_to_dict` and JSON Inference v1 (ADR-020) are deferred to L3.4. A G3 GO is **not** a G4 codec qualification.

Passing a pure transition does **not** demonstrate that a remote model produced a result.
