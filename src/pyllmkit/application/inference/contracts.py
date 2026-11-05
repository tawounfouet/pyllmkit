"""Immutable P7 application execution boundary; no transport or SDK imports."""

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite

from pyllmkit.application.registry import DeploymentResolution
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import (
    CompatibilityReport,
    DeploymentId,
    InferenceRequest,
    InferenceRun,
    InferenceRunId,
)
from pyllmkit.domain.providers import ProviderId


class InvocationPreconditionError(ValueError):
    """Safe code-only rejection occurring before any adapter is invoked."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class InvocationPortError(Exception):
    """Sanitized failure raised by an adapter; never a native SDK exception."""

    def __init__(self, code: str) -> None:
        if type(code) is not str or not code or not code.isidentifier() or not code.islower():
            raise ValueError("invalid_safe_error_code")
        self.code = code
        super().__init__(code)


class InvocationCancelledError(Exception):
    """Adapter observed local cancellation; no remote cancellation is implied."""


@dataclass(frozen=True, slots=True)
class InvocationOptions:
    """Transport intent only. L7.1 deliberately supports a single attempt."""

    timeout_seconds: float = 30.0
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if (
            type(self.timeout_seconds) is not float
            or not isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0.0
        ):
            raise DomainValidationError("timeout_seconds must be a positive finite float")
        if type(self.max_attempts) is not int or self.max_attempts != 1:
            raise DomainValidationError("L7.1 supports exactly one attempt")


@dataclass(frozen=True, slots=True)
class InvocationContext:
    """Correlation outside the domain request, one RunId and one attempt at a time."""

    run_id: InferenceRunId
    deployment_id: DeploymentId
    provider_id: ProviderId | None
    attempt_id: str
    deadline: datetime
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.run_id) is not InferenceRunId:
            raise DomainValidationError("run_id must be InferenceRunId")
        if type(self.deployment_id) is not DeploymentId:
            raise DomainValidationError("deployment_id must be DeploymentId")
        if self.provider_id is not None and type(self.provider_id) is not ProviderId:
            raise DomainValidationError("provider_id must be ProviderId or None")
        if type(self.attempt_id) is not str or not self.attempt_id.strip():
            raise DomainValidationError("attempt_id must be nonblank")
        if (
            type(self.deadline) is not datetime
            or self.deadline.tzinfo is None
            or self.deadline.utcoffset() is None
        ):
            raise DomainValidationError("deadline must be timezone-aware")
        if self.trace_id is not None and (
            type(self.trace_id) is not str or not self.trace_id.strip()
        ):
            raise DomainValidationError("trace_id must be nonblank or None")

    def next_attempt(self, attempt_id: str) -> InvocationContext:
        """Prepare a *new* attempt ID without changing the logical RunId.

        L7.1 exercises the contract only; retry execution belongs to L7.7.
        """
        if type(attempt_id) is not str or not attempt_id.strip():
            raise DomainValidationError("next attempt_id must be nonblank")
        if attempt_id == self.attempt_id:
            raise DomainValidationError("attempt_id must change on a new attempt")
        return InvocationContext(
            self.run_id, self.deployment_id, self.provider_id,
            attempt_id, self.deadline, self.trace_id,
        )


@dataclass(frozen=True, slots=True)
class PreparedInvocation:
    """Validated deployment binding and immutable canonical request."""

    request: InferenceRequest = field(repr=False)
    resolution: DeploymentResolution = field(repr=False)
    native_model_alias: str = field(repr=False)
    context: InvocationContext
    parameter_assessment: CompatibilityReport = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.request) is not InferenceRequest:
            raise DomainValidationError("request must be InferenceRequest")
        if type(self.resolution) is not DeploymentResolution:
            raise DomainValidationError("resolution must be DeploymentResolution")
        if type(self.native_model_alias) is not str or not self.native_model_alias.strip():
            raise DomainValidationError("native_model_alias must be nonblank")
        if type(self.context) is not InvocationContext:
            raise DomainValidationError("context must be InvocationContext")
        if self.context.deployment_id != self.resolution.deployment.id:
            raise DomainValidationError("deployment binding mismatch")
        if self.context.provider_id != self.resolution.deployment.provider_id:
            raise DomainValidationError("provider binding mismatch")
        if type(self.parameter_assessment) is not CompatibilityReport:
            raise DomainValidationError("parameter_assessment must be CompatibilityReport")


@dataclass(frozen=True, slots=True)
class InferenceExecution:
    """Observed terminal Run. Errors are safe InferenceFailure codes on the Run."""

    run: InferenceRun = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.run) is not InferenceRun or not self.run.is_terminal:
            raise DomainValidationError("InferenceExecution requires a terminal InferenceRun")

    @property
    def response(self):  # type: ignore[no-untyped-def]
        """Use the Run's own response; do not create a second result identity."""
        return self.run.response
