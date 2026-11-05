"""Immutable requirements and evidence for deterministic deployment selection."""

from dataclasses import dataclass
from typing import TypeAlias

from pyllmkit.domain.capabilities import CapabilityId
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.modalities import Modality
from pyllmkit.domain.providers import ProviderId

from .errors import RegistryError
from .queries import CapabilityMatchMode


@dataclass(frozen=True, slots=True)
class DeploymentRequirement:
    """All supplied filters are hard constraints, never weighted preferences.

    AVAILABLE means catalog-declared status, not a live service healthcheck.
    A known but provisional context bound does not meet the strict requirement.
    """

    provider_id: ProviderId | None = None
    region: str | None = None
    runtime: str | None = None
    require_available: bool = True
    required_capabilities: tuple[CapabilityId, ...] = ()
    capability_mode: CapabilityMatchMode = CapabilityMatchMode.NATIVE_ONLY
    required_input_modalities: frozenset[Modality] = frozenset()
    required_output_modalities: frozenset[Modality] = frozenset()
    min_context_window: int | None = None

    def __post_init__(self) -> None:
        if self.provider_id is not None and not isinstance(self.provider_id, ProviderId):
            raise DomainValidationError("provider_id must be ProviderId or None")
        for label in ("region", "runtime"):
            value = getattr(self, label)
            if value is not None and (type(value) is not str or not value.strip()):
                raise DomainValidationError(f"{label} must be a nonblank string or None")
        if type(self.require_available) is not bool:
            raise DomainValidationError("require_available must be bool")
        if not isinstance(self.capability_mode, CapabilityMatchMode):
            raise DomainValidationError("capability_mode must be CapabilityMatchMode")
        if not isinstance(self.required_capabilities, tuple) or any(
            not isinstance(item, CapabilityId) for item in self.required_capabilities
        ):
            raise DomainValidationError("required_capabilities must be tuple[CapabilityId, ...]")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise DomainValidationError("duplicate CapabilityId in requirements")
        object.__setattr__(
            self, "required_capabilities",
            tuple(sorted(self.required_capabilities, key=lambda item: item.value)),
        )
        for label in ("required_input_modalities", "required_output_modalities"):
            values = getattr(self, label)
            if not isinstance(values, frozenset) or any(
                not isinstance(item, Modality) for item in values
            ):
                raise DomainValidationError(f"{label} must be frozenset[Modality]")
        if self.min_context_window is not None and (
            type(self.min_context_window) is not int or self.min_context_window < 0
        ):
            raise DomainValidationError("min_context_window must be nonnegative int or None")


@dataclass(frozen=True, slots=True)
class CandidateRejection:
    """Safe reason codes without raw model metadata or credentials."""

    deployment_id: DeploymentId
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeploymentResolutionReport:
    """Complete deterministic candidate list, with no ranking or fallback."""

    considered: tuple[DeploymentId, ...]
    eligible: tuple[DeploymentId, ...]
    rejected: tuple[CandidateRejection, ...]
    selected_id: DeploymentId | None


class DeploymentResolutionError(RegistryError):
    """A documented selection failure, optionally carrying safe evidence."""

    def __init__(self, message: str, report: DeploymentResolutionReport | None = None) -> None:
        super().__init__(message)
        self.report = report


class ModelNotFoundError(DeploymentResolutionError):
    """Requested canonical model is absent from the catalog."""


class DeploymentNotFoundError(DeploymentResolutionError):
    """Requested exact deployment is absent from the catalog."""


class NoCompatibleDeploymentError(DeploymentResolutionError):
    """No candidate satisfies all explicit, conservative requirements."""


class AmbiguousDeploymentError(DeploymentResolutionError):
    """More than one candidate satisfies the hard requirements."""


ResolutionError: TypeAlias = DeploymentResolutionError
