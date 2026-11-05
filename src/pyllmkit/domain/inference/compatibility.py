"""Explicit offline parameter compatibility check (ADR-021 option A, AC-007).

This is not a provider capability resolver: the caller supplies a trusted
snapshot for precisely the target under assessment, and missing fields remain
UNKNOWN. No inference request is executed by this module.
"""

from dataclasses import dataclass

from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError

from .request import InferenceRequest
from .targets import DeploymentTarget, EndpointTarget, InferenceTarget, ModelTarget

GENERATION_PARAMETER_NAMES = (
    "temperature",
    "top_p",
    "top_k",
    "max_output_tokens",
    "seed",
    "stop_sequences",
    "presence_penalty",
    "frequency_penalty",
)


@dataclass(frozen=True, slots=True)
class ParameterSupport:
    """Caller-declared support for one allowed generation parameter."""

    name: str
    support: CapabilitySupport

    def __post_init__(self) -> None:
        if type(self.name) is not str or self.name not in GENERATION_PARAMETER_NAMES:
            raise DomainValidationError("unknown generation parameter name")
        if type(self.support) is not CapabilitySupport:
            raise DomainValidationError("ParameterSupport.support must be CapabilitySupport")


@dataclass(frozen=True, slots=True)
class GenerationSupportSnapshot:
    """Immutable set of declarations supplied for a specific typed target."""

    target: InferenceTarget
    parameters: tuple[ParameterSupport, ...] = ()

    def __post_init__(self) -> None:
        if type(self.target) not in (ModelTarget, DeploymentTarget, EndpointTarget):
            raise DomainValidationError("GenerationSupportSnapshot.target must be InferenceTarget")
        if type(self.parameters) is not tuple or any(
            type(item) is not ParameterSupport for item in self.parameters
        ):
            raise DomainValidationError("parameters must be a tuple of ParameterSupport")
        names = [item.name for item in self.parameters]
        if len(names) != len(set(names)):
            raise DomainValidationError("duplicate parameter support declaration")


@dataclass(frozen=True, slots=True)
class ParameterAssessment:
    """Observed support level for a parameter actually present in a request."""

    name: str
    level: SupportLevel | None

    def __post_init__(self) -> None:
        if type(self.name) is not str or self.name not in GENERATION_PARAMETER_NAMES:
            raise DomainValidationError("invalid assessed parameter name")
        if self.level is not None and type(self.level) is not SupportLevel:
            raise DomainValidationError("assessment level must be SupportLevel or None")


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    """Pure parameter report; never claims an unknown target is executable."""

    assessments: tuple[ParameterAssessment, ...]

    def __post_init__(self) -> None:
        if type(self.assessments) is not tuple or any(
            type(item) is not ParameterAssessment for item in self.assessments
        ):
            raise DomainValidationError("assessments must be a tuple of ParameterAssessment")
        names = [item.name for item in self.assessments]
        if len(names) != len(set(names)):
            raise DomainValidationError("duplicate parameter assessment")

    @property
    def unsupported_parameters(self) -> tuple[str, ...]:
        return tuple(
            item.name for item in self.assessments if item.level is SupportLevel.UNSUPPORTED
        )

    @property
    def unknown_parameters(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.assessments if item.level is None)

    @property
    def is_confirmed_native(self) -> bool:
        return bool(self.assessments) and all(
            item.level is SupportLevel.NATIVE for item in self.assessments
        )

    @property
    def is_compatible(self) -> bool | None:
        """False if explicitly unsupported, True if nonempty/all native, else UNKNOWN."""
        if self.unsupported_parameters:
            return False
        if self.is_confirmed_native:
            return True
        return None

    def reject_unsupported(self) -> None:
        """Fail only on a known unsupported parameter, never drop it silently."""
        if self.unsupported_parameters:
            # The name is from a fixed allowlist, never user-supplied prompt data.
            raise DomainValidationError(
                f"unsupported generation parameter: {self.unsupported_parameters[0]}"
            )


def evaluate_request_support(
    request: InferenceRequest, snapshot: GenerationSupportSnapshot
) -> CompatibilityReport:
    """Evaluate only explicitly supplied support levels for the exact target."""
    if type(request) is not InferenceRequest:
        raise DomainValidationError("expected an InferenceRequest")
    if type(snapshot) is not GenerationSupportSnapshot:
        raise DomainValidationError("expected a GenerationSupportSnapshot")
    if request.target != snapshot.target:
        raise DomainValidationError("support snapshot target does not match request target")
    if request.generation_config is None:
        return CompatibilityReport(())
    declared = {item.name: item.support.level for item in snapshot.parameters}
    assessments = tuple(
        ParameterAssessment(name, declared.get(name))
        for name in GENERATION_PARAMETER_NAMES
        if getattr(request.generation_config, name) is not None
    )
    return CompatibilityReport(assessments)


def validate_request_support(
    request: InferenceRequest, snapshot: GenerationSupportSnapshot
) -> CompatibilityReport:
    """Reject known UNSUPPORTED config and surface UNKNOWN/PARTIAL without inventing support."""
    report = evaluate_request_support(request, snapshot)
    report.reject_unsupported()
    return report
