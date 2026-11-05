"""ADR-019 direct-snapshot reconstitution must enforce all invariants.

Codec L3.4 will reconstruct these snapshots through validated constructors,
not by bypassing the aggregate's state/date/payload checks.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import cast

import pytest

from pyllmkit.domain import (
    Content,
    DomainValidationError,
    InferenceFailure,
    InferenceRequest,
    InferenceResponse,
    InferenceRun,
    InferenceRunId,
    InferenceRunState,
    Message,
    ModelId,
    ModelTarget,
    Role,
    TextContent,
    TextOutput,
)

T0 = datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(seconds=1)
T2 = T0 + timedelta(seconds=2)


def request() -> InferenceRequest:
    return InferenceRequest(
        ModelTarget(ModelId("model")),
        (Message(Role.USER, Content((TextContent("text"),))),),
    )


def _new(**overrides: object) -> InferenceRun:
    fields: dict[str, object] = {"run_id": InferenceRunId("id"), "request": request()}
    fields.update(overrides)
    return InferenceRun(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid", [None, "id", False, 5])
def test_direct_constructor_rejects_invalid_run_id(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="run_id"):
        _new(run_id=invalid)


@pytest.mark.parametrize("invalid", [None, "request", True, {}])
def test_direct_constructor_rejects_invalid_request(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="request"):
        _new(request=invalid)


@pytest.mark.parametrize("invalid", ["running", None, False, 1])
def test_direct_constructor_rejects_untyped_run_state(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="state"):
        _new(state=invalid)


@pytest.mark.parametrize("name", ["started_at", "streaming_started_at", "finished_at"])
@pytest.mark.parametrize("invalid", [datetime(2026, 11, 5), "date", 5, False])
def test_any_timestamp_requires_aware_datetime(name: str, invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="timezone-aware"):
        _new(**{name: invalid})


def test_created_cannot_contain_execution_dates_or_payloads() -> None:
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(started_at=T0)
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(streaming_started_at=T0)
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(finished_at=T1)
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(failure=InferenceFailure("error"))
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(response=InferenceResponse(InferenceRunId("id"), TextOutput("ok")))
    with pytest.raises(DomainValidationError, match="CREATED"):
        _new(cancellation_reason_code="user_request")


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"finished_at": T2},
        {"streaming_started_at": T1},
        {"failure": InferenceFailure("timeout")},
        {"response": InferenceResponse(InferenceRunId("id"), TextOutput("ok"))},
        {"cancellation_reason_code": "user_request"},
    ],
)
def test_running_requires_only_start_timestamp(kwargs: dict[str, object]) -> None:
    with pytest.raises(DomainValidationError, match="RUNNING"):
        _new(state=InferenceRunState.RUNNING, **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"started_at": T0},
        {"streaming_started_at": T1},
        {"started_at": T0, "streaming_started_at": T1, "finished_at": T2},
        {"started_at": T0, "streaming_started_at": T1, "failure": InferenceFailure("timeout")},
    ],
)
def test_streaming_requires_only_start_and_stream_timestamps(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(DomainValidationError, match="STREAMING"):
        _new(state=InferenceRunState.STREAMING, **kwargs)


@pytest.mark.parametrize("state", [
    InferenceRunState.COMPLETED, InferenceRunState.FAILED, InferenceRunState.CANCELLED,
])
def test_all_terminal_states_require_started_and_finished(state: InferenceRunState) -> None:
    with pytest.raises(DomainValidationError, match="terminal"):
        _new(state=state)
    with pytest.raises(DomainValidationError, match="terminal"):
        _new(state=state, started_at=T0)
    with pytest.raises(DomainValidationError, match="terminal"):
        _new(state=state, finished_at=T2)


def test_completed_requires_correct_response_exclusively() -> None:
    base = {
        "state": InferenceRunState.COMPLETED, "started_at": T0, "finished_at": T2,
    }
    with pytest.raises(DomainValidationError, match="COMPLETED"):
        _new(**base)
    with pytest.raises(DomainValidationError, match="COMPLETED"):
        _new(**base, response=InferenceResponse(InferenceRunId("id"), TextOutput("")), failure=InferenceFailure("error"))
    with pytest.raises(DomainValidationError, match="cancellation"):
        _new(**base, response=InferenceResponse(InferenceRunId("id"), TextOutput("")), cancellation_reason_code="user_request")
    with pytest.raises(DomainValidationError, match="response.run_id"):
        _new(**base, response=InferenceResponse(InferenceRunId("other"), TextOutput("")))


def test_failed_requires_failure_and_excludes_response_or_cancel() -> None:
    base = {"state": InferenceRunState.FAILED, "started_at": T0, "finished_at": T2}
    with pytest.raises(DomainValidationError, match="FAILED"):
        _new(**base)
    with pytest.raises(DomainValidationError, match="FAILED"):
        _new(**base, failure=InferenceFailure("timeout"), response=InferenceResponse(InferenceRunId("id"), TextOutput("bad")))
    with pytest.raises(DomainValidationError, match="cancellation"):
        _new(**base, failure=InferenceFailure("timeout"), cancellation_reason_code="user_request")


def test_cancelled_excludes_response_and_failure() -> None:
    base = {"state": InferenceRunState.CANCELLED, "started_at": T0, "finished_at": T2}
    with pytest.raises(DomainValidationError, match="CANCELLED"):
        _new(**base, response=InferenceResponse(InferenceRunId("id"), TextOutput("")))
    with pytest.raises(DomainValidationError, match="CANCELLED"):
        _new(**base, failure=InferenceFailure("timeout"))
    assert _new(**base).cancellation_reason_code is None
    assert _new(**base, cancellation_reason_code="user_request").cancellation_reason_code == "user_request"


def test_timestamp_order_checked_for_direct_snapshots() -> None:
    with pytest.raises(DomainValidationError, match="precedes"):
        _new(state=InferenceRunState.STREAMING, started_at=T1, streaming_started_at=T0)
    with pytest.raises(DomainValidationError, match="precedes"):
        _new(state=InferenceRunState.FAILED, started_at=T2, finished_at=T1, failure=InferenceFailure("timeout"))
    with pytest.raises(DomainValidationError, match="precedes"):
        _new(
            state=InferenceRunState.CANCELLED, started_at=T0,
            streaming_started_at=T2, finished_at=T1,
        )


def test_invalid_reconstructed_snapshot_is_rejected_on_replace() -> None:
    completed = _new(
        state=InferenceRunState.COMPLETED, started_at=T0, finished_at=T2,
        response=InferenceResponse(InferenceRunId("id"), TextOutput("done")),
    )
    with pytest.raises(DomainValidationError, match="response.run_id"):
        replace(
            completed,
            response=InferenceResponse(InferenceRunId("foreign-run"), TextOutput("wrong")),
        )
    assert completed.response is not None
    assert completed.response.run_id == completed.run_id


def test_six_reconstructible_consistent_snapshots() -> None:
    identity = InferenceRunId("id")
    response = InferenceResponse(identity, TextOutput("done"))
    cases = (
        {},
        {"state": InferenceRunState.RUNNING, "started_at": T0},
        {"state": InferenceRunState.STREAMING, "started_at": T0, "streaming_started_at": T1},
        {"state": InferenceRunState.COMPLETED, "started_at": T0, "finished_at": T2, "response": response},
        {"state": InferenceRunState.FAILED, "started_at": T0, "finished_at": T2, "failure": InferenceFailure("timeout")},
        {"state": InferenceRunState.CANCELLED, "started_at": T0, "streaming_started_at": T1, "finished_at": T2},
    )
    actual = tuple(_new(**case) for case in cases)
    assert tuple(x.state for x in actual) == tuple(InferenceRunState)
    assert all(x.run_id == identity for x in actual)
    assert all(x == actual[0] for x in actual)
    assert len({*actual}) == 1


@pytest.mark.parametrize("bad", ["", " ", "RAW:TOKEN", "vendor.error", "UPPER", "1bad", None, True])
def test_failure_code_must_be_normalized(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="InferenceFailure.code"):
        InferenceFailure(cast(str, bad))


def test_failure_is_strict_immutable_hashable_and_redacted() -> None:
    failure = InferenceFailure("network_timeout")
    assert failure == InferenceFailure("network_timeout")
    assert hash(failure) == hash(InferenceFailure("network_timeout"))
    assert failure.code == "network_timeout"
    assert "network_timeout" not in repr(failure)


@pytest.mark.parametrize("bad", ["", " ", "operator:raw", "UPPER", True, 9])
def test_cancel_code_must_be_normalized(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="cancellation_reason_code"):
        _new(
            state=InferenceRunState.CANCELLED, started_at=T0,
            finished_at=T2, cancellation_reason_code=bad,
        )
