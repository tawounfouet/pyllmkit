"""ADR-019 state transition matrix, identity and timestamps."""

from dataclasses import FrozenInstanceError, replace
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
        ModelTarget(ModelId("offline/llm")),
        (Message(Role.USER, Content((TextContent("confidential prompt"),))),),
    )


def created(run_id: str = "run-001") -> InferenceRun:
    return InferenceRun(InferenceRunId(run_id), request())


def running(run_id: str = "run-001") -> InferenceRun:
    return created(run_id).start(T0)


def streaming() -> InferenceRun:
    return running().begin_stream(T1)


def completed() -> InferenceRun:
    run = running()
    return run.complete(InferenceResponse(run.run_id, TextOutput("secret output")), T2)


def failed() -> InferenceRun:
    return running().fail(InferenceFailure("timeout"), T2)


def cancelled() -> InferenceRun:
    return running().cancel(T2)


def test_state_enum_is_closed_and_terminal_property() -> None:
    assert len(InferenceRunState) == 6
    assert tuple(x.value for x in InferenceRunState) == (
        "created", "running", "streaming", "completed", "failed", "cancelled"
    )
    for item in (created(), running(), streaming()):
        assert not item.is_terminal
    for item in (completed(), failed(), cancelled()):
        assert item.is_terminal


@pytest.mark.parametrize(
    ("state", "action"),
    [
        ("created", "start"),
        ("running", "begin_stream"),
        ("running", "complete"),
        ("running", "fail"),
        ("running", "cancel"),
        ("streaming", "complete"),
        ("streaming", "fail"),
        ("streaming", "cancel"),
    ],
)
def test_only_eight_defined_transitions_succeed(state: str, action: str) -> None:
    source = {"created": created, "running": running, "streaming": streaming}[state]()
    if action == "start":
        result = source.start(T1)
        assert result.state is InferenceRunState.RUNNING
    elif action == "begin_stream":
        result = source.begin_stream(T2)
        assert result.state is InferenceRunState.STREAMING
    elif action == "complete":
        result = source.complete(InferenceResponse(source.run_id, TextOutput("")), T2)
        assert result.state is InferenceRunState.COMPLETED
    elif action == "fail":
        result = source.fail(InferenceFailure("network_error"), T2)
        assert result.state is InferenceRunState.FAILED
    else:
        result = source.cancel(T2)
        assert result.state is InferenceRunState.CANCELLED
    assert source != created("other-run")
    assert source == result
    assert source is not result


@pytest.mark.parametrize("factory", [created, running, streaming, completed, failed, cancelled])
@pytest.mark.parametrize("action", ["start", "begin_stream", "complete", "fail", "cancel"])
def test_all_unsupported_state_action_pairs_reject(
    factory: type | object, action: str
) -> None:
    source = factory()  # type: ignore[operator]
    legal = {
        ("created", "start"),
        ("running", "begin_stream"),
        ("running", "complete"),
        ("running", "fail"),
        ("running", "cancel"),
        ("streaming", "complete"),
        ("streaming", "fail"),
        ("streaming", "cancel"),
    }
    if (source.state.value, action) in legal:
        return
    with pytest.raises(DomainValidationError, match="transition"):
        if action == "start":
            source.start(T2)
        elif action == "begin_stream":
            source.begin_stream(T2)
        elif action == "complete":
            source.complete(InferenceResponse(source.run_id, TextOutput("x")), T2)
        elif action == "fail":
            source.fail(InferenceFailure("failure"), T2)
        else:
            source.cancel(T2)


def test_streaming_path_accepts_failure_and_cancel_with_preserved_history() -> None:
    state = streaming()
    failure = state.fail(InferenceFailure("timeout"), T2)
    abort = state.cancel(T2, "operator_request")
    assert failure.state is InferenceRunState.FAILED
    assert failure.streaming_started_at == T1
    assert failure.finished_at == T2
    assert abort.state is InferenceRunState.CANCELLED
    assert abort.streaming_started_at == T1
    assert abort.cancellation_reason_code == "operator_request"
    assert state.finished_at is None


@pytest.mark.parametrize("terminal_factory", [completed, failed, cancelled])
def test_all_terminal_runs_are_irreversible(terminal_factory: type | object) -> None:
    terminal = terminal_factory()  # type: ignore[operator]
    for call in (
        lambda: terminal.start(T2),
        lambda: terminal.begin_stream(T2),
        lambda: terminal.complete(InferenceResponse(terminal.run_id, TextOutput("x")), T2),
        lambda: terminal.fail(InferenceFailure("failure"), T2),
        lambda: terminal.cancel(T2),
    ):
        with pytest.raises(DomainValidationError, match="transition"):
            call()


@pytest.mark.parametrize("attempt", [1, 2, 100])
def test_attempt_is_explicit_positive_integer(attempt: int) -> None:
    run = InferenceRun(InferenceRunId("a"), request(), attempt=attempt)
    assert run.attempt == attempt
    assert run.state is InferenceRunState.CREATED


@pytest.mark.parametrize("invalid", [0, -1, False, True, 1.0, "1", None])
def test_attempt_must_be_exact_positive_integer(invalid: object) -> None:
    with pytest.raises(DomainValidationError, match="attempt"):
        InferenceRun(InferenceRunId("a"), request(), attempt=cast(int, invalid))


def test_equality_and_hash_are_by_identity_not_snapshot_state() -> None:
    one = created()
    two = one.start(T0)
    three = two.cancel(T2)
    assert one is not two and two is not three
    assert one == two == three
    assert len({one, two, three}) == 1
    assert one.same_identity_as(three)
    assert not one.same_identity_as(created("another"))
    assert not one.same_identity_as(None)
    assert one != object()
    assert one.started_at is None
    assert three.started_at == T0


def test_same_identity_different_request_does_not_mean_same_snapshot() -> None:
    original = created("same-id")
    alternative = InferenceRun(
        original.run_id,
        InferenceRequest(
            ModelTarget(ModelId("another")),
            (Message(Role.USER, Content((TextContent("other"),))),),
        ),
    )
    assert original == alternative
    assert original.request != alternative.request


def test_replacing_snapshot_cannot_bypass_invariants() -> None:
    current = running()
    with pytest.raises(DomainValidationError, match="COMPLETED"):
        replace(current, state=InferenceRunState.COMPLETED, finished_at=T2)
    with pytest.raises(DomainValidationError, match="CREATED"):
        replace(current, state=InferenceRunState.CREATED)
    assert current.state is InferenceRunState.RUNNING


def test_immutable_and_private_fields_excluded_from_repr() -> None:
    run = completed()
    assert "confidential prompt" not in repr(run)
    assert "secret output" not in repr(run)
    assert "secret output" not in repr(run.response)
    with pytest.raises(FrozenInstanceError):
        run.finished_at = T0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("at", "match"),
    [
        (datetime(2026, 11, 5, 11, 0), "timezone-aware"),
        (None, "timezone-aware"),
        ("2026-11-05", "timezone-aware"),
    ],
)
def test_clock_must_be_aware_and_explicit(at: object, match: str) -> None:
    with pytest.raises(DomainValidationError, match=match):
        created().start(cast(datetime, at))


def test_offset_aware_clock_is_accepted_and_ordered_by_instant() -> None:
    paris = timezone(timedelta(hours=1))
    start = datetime(2026, 11, 5, 12, 0, tzinfo=paris)
    end = datetime(2026, 11, 5, 11, 0, tzinfo=timezone.utc)
    run = created().start(start)
    done = run.complete(InferenceResponse(run.run_id, TextOutput("")), end)
    assert done.started_at == done.finished_at


@pytest.mark.parametrize("factory", [running, streaming])
def test_transition_cannot_move_backward_in_time(factory: type | object) -> None:
    current = factory()  # type: ignore[operator]
    before = T0 - timedelta(microseconds=1)
    with pytest.raises(DomainValidationError, match="timestamp"):
        current.cancel(before)


def test_streaming_timestamp_must_not_precede_start() -> None:
    with pytest.raises(DomainValidationError, match="timestamp"):
        running().begin_stream(T0 - timedelta(seconds=1))


def test_terminal_timestamp_must_not_precede_stream() -> None:
    with pytest.raises(DomainValidationError, match="timestamp"):
        streaming().fail(InferenceFailure("timeout"), T0)


def test_transition_type_rejections_dont_change_current_snapshot() -> None:
    current = running()
    with pytest.raises(DomainValidationError, match="complete.response"):
        current.complete(cast(InferenceResponse, None), T1)
    with pytest.raises(DomainValidationError, match="fail.failure"):
        current.fail(cast(InferenceFailure, "oops"), T1)
    with pytest.raises(DomainValidationError, match="cancellation_reason_code"):
        current.cancel(T1, "RAW:token")
    assert current.state is InferenceRunState.RUNNING
    assert current.finished_at is None
