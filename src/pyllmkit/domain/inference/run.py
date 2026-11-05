"""Immutable InferenceRun aggregate and pure state transitions (ADR-014/019).

An InferenceRun is one logical execution identity. Transitions return validated
snapshots, without executing an inference, opening sockets or publishing events.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Self

from pyllmkit.domain.errors import DomainValidationError

from .failure import InferenceFailure, validate_reason_code
from .identifiers import InferenceRunId
from .request import InferenceRequest
from .response import InferenceResponse


class InferenceRunState(StrEnum):
    """Closed lifecycle vocabulary; STREAMING is descriptive, not real transport."""

    CREATED = "created"
    RUNNING = "running"
    STREAMING = "streaming"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = frozenset(
    (InferenceRunState.COMPLETED, InferenceRunState.FAILED, InferenceRunState.CANCELLED)
)


def _require_aware_at(value: datetime, name: str) -> None:
    """Reject naive and non-datetime timestamps without reading the system clock."""
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{name} must be a timezone-aware datetime")


@dataclass(frozen=True, slots=True, eq=False)
class InferenceRun:
    """An Entity/Aggregate Root with immutable snapshots and RunId equality.

    Equality/hash identify the same run, not the same snapshot state. Inspect
    state and timestamps explicitly when verifying a lifecycle transition.
    """

    run_id: InferenceRunId
    request: InferenceRequest = field(repr=False)
    attempt: int = 1
    state: InferenceRunState = InferenceRunState.CREATED
    started_at: datetime | None = None
    streaming_started_at: datetime | None = None
    finished_at: datetime | None = None
    response: InferenceResponse | None = field(default=None, repr=False)
    failure: InferenceFailure | None = field(default=None, repr=False)
    cancellation_reason_code: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("InferenceRun.run_id must be InferenceRunId")
        if type(self.request) is not InferenceRequest:
            raise DomainValidationError("InferenceRun.request must be InferenceRequest")
        if type(self.attempt) is not int or self.attempt < 1:
            raise DomainValidationError("InferenceRun.attempt must be an int >= 1")
        if type(self.state) is not InferenceRunState:
            raise DomainValidationError("InferenceRun.state must be InferenceRunState")

        for name in ("started_at", "streaming_started_at", "finished_at"):
            value = getattr(self, name)
            if value is not None:
                _require_aware_at(value, f"InferenceRun.{name}")

        if self.response is not None and type(self.response) is not InferenceResponse:
            raise DomainValidationError("InferenceRun.response must be InferenceResponse or None")
        if self.failure is not None and type(self.failure) is not InferenceFailure:
            raise DomainValidationError("InferenceRun.failure must be InferenceFailure or None")
        if self.cancellation_reason_code is not None:
            validate_reason_code(self.cancellation_reason_code, "cancellation_reason_code")

        if self.started_at is not None and self.streaming_started_at is not None:
            if self.streaming_started_at < self.started_at:
                raise DomainValidationError("streaming_started_at precedes started_at")
        if self.started_at is not None and self.finished_at is not None:
            if self.finished_at < self.started_at:
                raise DomainValidationError("finished_at precedes started_at")
        if self.streaming_started_at is not None and self.finished_at is not None:
            if self.finished_at < self.streaming_started_at:
                raise DomainValidationError("finished_at precedes streaming_started_at")

        if self.state is InferenceRunState.CREATED:
            if any(
                value is not None
                for value in (
                    self.started_at, self.streaming_started_at, self.finished_at,
                    self.response, self.failure, self.cancellation_reason_code,
                )
            ):
                raise DomainValidationError("CREATED must not contain execution data")
        elif self.state is InferenceRunState.RUNNING:
            if self.started_at is None or any(
                value is not None
                for value in (
                    self.streaming_started_at, self.finished_at, self.response,
                    self.failure, self.cancellation_reason_code,
                )
            ):
                raise DomainValidationError("RUNNING requires only started_at")
        elif self.state is InferenceRunState.STREAMING:
            if self.started_at is None or self.streaming_started_at is None or any(
                value is not None
                for value in (
                    self.finished_at, self.response, self.failure,
                    self.cancellation_reason_code,
                )
            ):
                raise DomainValidationError("STREAMING requires start and stream timestamps")
        elif self.state in _TERMINAL_STATES:
            if self.started_at is None or self.finished_at is None:
                raise DomainValidationError("terminal run requires started_at and finished_at")
            if self.state is InferenceRunState.COMPLETED:
                if self.response is None or self.failure is not None:
                    raise DomainValidationError("COMPLETED requires response and no failure")
                if self.cancellation_reason_code is not None:
                    raise DomainValidationError("COMPLETED cannot have a cancellation reason")
                if self.response.run_id != self.run_id:
                    raise DomainValidationError("response.run_id must match InferenceRun.run_id")
            elif self.state is InferenceRunState.FAILED:
                if self.failure is None or self.response is not None:
                    raise DomainValidationError("FAILED requires failure and no response")
                if self.cancellation_reason_code is not None:
                    raise DomainValidationError("FAILED cannot have a cancellation reason")
            elif self.response is not None or self.failure is not None:
                raise DomainValidationError("CANCELLED cannot have response or failure")

    def __eq__(self, other: object) -> bool:
        """Entity identity (not snapshot structural equality)."""
        if not isinstance(other, InferenceRun):
            return NotImplemented
        return self.run_id == other.run_id

    def __hash__(self) -> int:
        return hash(self.run_id)

    def same_identity_as(self, other: object) -> bool:
        """Explicitly compare Run identities, not states or request content."""
        return isinstance(other, InferenceRun) and self.run_id == other.run_id

    @property
    def is_terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    def _require_state(self, *allowed: InferenceRunState) -> None:
        if self.state not in allowed:
            raise DomainValidationError("illegal InferenceRun state transition")

    def _validate_event_time(self, at: datetime) -> None:
        _require_aware_at(at, "transition.at")
        last = self.streaming_started_at or self.started_at
        if last is not None and at < last:
            raise DomainValidationError("transition.at precedes previous timestamp")

    def start(self, at: datetime) -> Self:
        """Pure CREATED -> RUNNING; a time is always supplied by the caller."""
        self._require_state(InferenceRunState.CREATED)
        self._validate_event_time(at)
        return replace(self, state=InferenceRunState.RUNNING, started_at=at)

    def begin_stream(self, at: datetime) -> Self:
        """Pure RUNNING -> STREAMING, without starting an actual stream."""
        self._require_state(InferenceRunState.RUNNING)
        self._validate_event_time(at)
        return replace(self, state=InferenceRunState.STREAMING, streaming_started_at=at)

    def complete(self, response: InferenceResponse, at: datetime) -> Self:
        """Complete only the matching run, without asserting any provider invocation."""
        self._require_state(InferenceRunState.RUNNING, InferenceRunState.STREAMING)
        if type(response) is not InferenceResponse:
            raise DomainValidationError("complete.response must be InferenceResponse")
        if response.run_id != self.run_id:
            raise DomainValidationError("response.run_id must match InferenceRun.run_id")
        self._validate_event_time(at)
        return replace(
            self,
            state=InferenceRunState.COMPLETED,
            finished_at=at,
            response=response,
        )

    def fail(self, failure: InferenceFailure, at: datetime) -> Self:
        """Record a normalized failure; never serialize native exceptions."""
        self._require_state(InferenceRunState.RUNNING, InferenceRunState.STREAMING)
        if type(failure) is not InferenceFailure:
            raise DomainValidationError("fail.failure must be InferenceFailure")
        self._validate_event_time(at)
        return replace(
            self, state=InferenceRunState.FAILED, finished_at=at, failure=failure
        )

    def cancel(self, at: datetime, cancellation_reason_code: str | None = None) -> Self:
        """Record local CANCELLED state; does not interrupt any remote execution."""
        self._require_state(InferenceRunState.RUNNING, InferenceRunState.STREAMING)
        if cancellation_reason_code is not None:
            validate_reason_code(cancellation_reason_code, "cancellation_reason_code")
        self._validate_event_time(at)
        return replace(
            self,
            state=InferenceRunState.CANCELLED,
            finished_at=at,
            cancellation_reason_code=cancellation_reason_code,
        )
