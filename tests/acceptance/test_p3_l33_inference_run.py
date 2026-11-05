"""P3-AC-014..020 and AC-029: pure inference execution lifecycle."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

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

START = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
FINISH = START + timedelta(seconds=2)


def _request() -> InferenceRequest:
    return InferenceRequest(
        ModelTarget(ModelId("offline-model")),
        (Message(Role.USER, Content((TextContent("private prompt"),))),),
    )


def _run(value: str, request: InferenceRequest) -> InferenceRun:
    return InferenceRun(InferenceRunId(value), request)


def test_p3_ac014_two_runs_can_share_one_request_with_distinct_identities() -> None:
    request = _request()
    one, two = _run("run-a", request), _run("run-b", request)
    assert one.request is two.request is request
    assert one.run_id != two.run_id
    assert one != two
    assert one.state is two.state is InferenceRunState.CREATED


def test_p3_ac015_created_running_completed_with_correlated_response() -> None:
    created = _run("run-015", _request())
    running = created.start(START)
    response = InferenceResponse(created.run_id, TextOutput("Bonjour"))
    completed = running.complete(response, FINISH)
    assert created.state is InferenceRunState.CREATED
    assert created.started_at is None
    assert running.state is InferenceRunState.RUNNING
    assert running.started_at == START
    assert completed.state is InferenceRunState.COMPLETED
    assert completed.response is response
    assert completed.failure is None
    assert completed.finished_at == FINISH
    assert completed.is_terminal
    assert created == running == completed  # Entity identity, not snapshot equality.
    assert hash(created) == hash(completed)


def test_p3_ac016_failed_run_has_normalized_failure_and_no_response() -> None:
    failed = _run("run-016", _request()).start(START).fail(
        InferenceFailure("provider_unavailable"), FINISH
    )
    assert failed.state is InferenceRunState.FAILED
    assert failed.failure == InferenceFailure("provider_unavailable")
    assert failed.response is None
    assert failed.finished_at == FINISH
    assert failed.is_terminal


def test_p3_ac017_cancelled_run_is_terminal_and_no_remote_cancel_claim() -> None:
    cancelled = _run("run-017", _request()).start(START).cancel(
        FINISH, cancellation_reason_code="user_request"
    )
    assert cancelled.state is InferenceRunState.CANCELLED
    assert cancelled.cancellation_reason_code == "user_request"
    assert cancelled.finished_at == FINISH
    assert cancelled.response is None
    assert cancelled.failure is None
    assert cancelled.is_terminal


def test_p3_ac018_completed_cannot_be_restarted() -> None:
    created = _run("run-018", _request())
    completed = created.start(START).complete(
        InferenceResponse(created.run_id, TextOutput("")), FINISH
    )
    with pytest.raises(DomainValidationError, match="transition"):
        completed.start(FINISH)
    assert completed.state is InferenceRunState.COMPLETED


def test_p3_ac019_mismatched_response_run_id_rejected() -> None:
    running = _run("run-019", _request()).start(START)
    alien = InferenceResponse(InferenceRunId("other"), TextOutput("wrong"))
    with pytest.raises(DomainValidationError, match="response.run_id"):
        running.complete(alien, FINISH)
    assert running.state is InferenceRunState.RUNNING
    assert running.response is None


def test_p3_ac020_replay_same_request_keeps_intention_immutable() -> None:
    request = _request()
    first = _run("attempt-one", request).start(START)
    second = _run("attempt-two", request).start(START + timedelta(seconds=1))
    assert first.request is second.request is request
    assert first.run_id != second.run_id
    assert request.messages[0].content.parts[0] == TextContent("private prompt")
    with pytest.raises(FrozenInstanceError):
        request.messages = ()  # type: ignore[misc]


def test_p3_ac029_all_clocks_injected_and_reproducible() -> None:
    request = _request()
    stream_time = START + timedelta(milliseconds=250)
    end_time = START + timedelta(seconds=1)
    run = _run("run-029", request).start(START).begin_stream(stream_time)
    completed = run.complete(InferenceResponse(run.run_id, TextOutput("done")), end_time)
    assert run.state is InferenceRunState.STREAMING
    assert run.streaming_started_at == stream_time
    assert completed.finished_at == end_time
    assert completed.started_at == START
    assert completed.streaming_started_at == stream_time
    assert completed.state is InferenceRunState.COMPLETED
    assert run.finished_at is None
    assert _run("run-029", request).start(START).begin_stream(stream_time) == completed
