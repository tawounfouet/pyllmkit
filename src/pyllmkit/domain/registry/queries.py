"""Strongly typed, immutable, deterministic catalog queries (P6 L6.3).

Queries are pure predicates over declared snapshots, not live routing. A
missing declaration cannot satisfy a positive strict requirement. Effective
capabilities across layers belong to the later P6 L6.4 resolver.
"""

from dataclasses import dataclass
from enum import StrEnum

from pyllmkit.domain.capabilities import CapabilityId, CapabilitySet, SupportLevel
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId
from pyllmkit.domain.providers import ProviderId


class CapabilityMatchMode(StrEnum):
    """Strict selection semantics for *declared*, not effective, capabilities."""

    NATIVE_ONLY = "native_only"
    USABLE = "usable"


def _validate_required(
    values: tuple[CapabilityId, ...], label: str
) -> tuple[CapabilityId, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, CapabilityId) for item in values
    ):
        raise DomainValidationError(f"{label} must be tuple[CapabilityId, ...]")
    if len({item.value for item in values}) != len(values):
        raise DomainValidationError(f"{label} must have unique CapabilityIds")
    return tuple(sorted(values, key=lambda cap: cap.value))


def _validate_modalities(values: frozenset[Modality], label: str) -> None:
    if not isinstance(values, frozenset) or any(
        not isinstance(modality, Modality) for modality in values
    ):
        raise DomainValidationError(f"{label} must be frozenset[Modality]")


def _valid_string(value: str | None, label: str) -> None:
    if value is not None and (type(value) is not str or not value.strip()):
        raise DomainValidationError(f"{label} must be a nonblank string or None")


def _match_capabilities(
    declared: CapabilitySet | None,
    required: tuple[CapabilityId, ...],
    mode: CapabilityMatchMode,
) -> bool:
    if not required:
        return True
    if declared is None:
        return False
    for capability_id in required:
        level = declared.support_of(capability_id).level
        if mode is CapabilityMatchMode.NATIVE_ONLY:
            if level is not SupportLevel.NATIVE:
                return False
        elif level not in {SupportLevel.NATIVE, SupportLevel.PARTIAL, SupportLevel.EMULATED}:
            return False
    return True


def _match_modalities(
    declared: ModalitySet | None,
    inputs: frozenset[Modality],
    outputs: frozenset[Modality],
) -> bool:
    if not inputs and not outputs:
        return True
    if declared is None:
        return False
    return all(declared.accepts_input(item) is True for item in inputs) and all(
        declared.can_output(item) is True for item in outputs
    )


@dataclass(frozen=True, slots=True)
class ModelQuery:
    """Conjunction of explicit criteria over logical Model snapshots.

    Provider selection is by *declared* ProviderModelRef aliases only. Alias
    strings are compared explicitly against ProviderId.value, without
    rewriting the logical ModelId or guessing from the developer name.
    """

    model_id: ModelId | None = None
    family: ModelFamily | None = None
    developer: str | None = None
    provider_id: ProviderId | None = None
    required_capabilities: tuple[CapabilityId, ...] = ()
    capability_mode: CapabilityMatchMode = CapabilityMatchMode.NATIVE_ONLY
    required_input_modalities: frozenset[Modality] = frozenset()
    required_output_modalities: frozenset[Modality] = frozenset()
    min_context_window: int | None = None

    def __post_init__(self) -> None:
        if self.model_id is not None and not isinstance(self.model_id, ModelId):
            raise DomainValidationError("model_id must be ModelId or None")
        if self.family is not None and not isinstance(self.family, ModelFamily):
            raise DomainValidationError("family must be ModelFamily or None")
        _valid_string(self.developer, "developer")
        if self.provider_id is not None and not isinstance(self.provider_id, ProviderId):
            raise DomainValidationError("provider_id must be ProviderId or None")
        if not isinstance(self.capability_mode, CapabilityMatchMode):
            raise DomainValidationError("capability_mode must be CapabilityMatchMode")
        object.__setattr__(
            self, "required_capabilities",
            _validate_required(self.required_capabilities, "required_capabilities"),
        )
        _validate_modalities(self.required_input_modalities, "required_input_modalities")
        _validate_modalities(self.required_output_modalities, "required_output_modalities")
        if self.min_context_window is not None and (
            type(self.min_context_window) is not int or self.min_context_window < 0
        ):
            raise DomainValidationError("min_context_window must be a nonnegative int or None")

    def __call__(self, model: Model) -> bool:
        if not isinstance(model, Model):
            raise DomainValidationError("ModelQuery requires Model")
        if self.model_id is not None and model.id != self.model_id:
            return False
        if self.family is not None and model.identity.family != self.family:
            return False
        if self.developer is not None and model.identity.developer != self.developer:
            return False
        if self.provider_id is not None and not any(
            alias.provider_id == self.provider_id.value and alias.model_id == model.id
            for alias in model.provider_refs
        ):
            return False
        if not _match_capabilities(
            model.capabilities, self.required_capabilities, self.capability_mode
        ):
            return False
        if not _match_modalities(
            model.modalities,
            self.required_input_modalities,
            self.required_output_modalities,
        ):
            return False
        if self.min_context_window is not None and (
            model.limits is None
            or model.limits.context_window is None
            or model.limits.context_window < self.min_context_window
        ):
            return False
        return True


@dataclass(frozen=True, slots=True)
class DeploymentQuery:
    """Strict AND criteria for declared deployment metadata only.

    A capability in Deployment.capabilities is a declared local constraint,
    not yet the effective intersection of Model/Provider/Deployment (L6.4).
    """

    deployment_id: DeploymentId | None = None
    model_id: ModelId | None = None
    provider_id: ProviderId | None = None
    status: DeploymentStatus | None = None
    region: str | None = None
    runtime: str | None = None
    required_capabilities: tuple[CapabilityId, ...] = ()
    capability_mode: CapabilityMatchMode = CapabilityMatchMode.NATIVE_ONLY
    required_input_modalities: frozenset[Modality] = frozenset()
    required_output_modalities: frozenset[Modality] = frozenset()

    def __post_init__(self) -> None:
        for value, kind, label in (
            (self.deployment_id, DeploymentId, "deployment_id"),
            (self.model_id, ModelId, "model_id"),
            (self.provider_id, ProviderId, "provider_id"),
            (self.status, DeploymentStatus, "status"),
        ):
            if value is not None and not isinstance(value, kind):
                raise DomainValidationError(f"{label} must be {kind.__name__} or None")
        _valid_string(self.region, "region")
        _valid_string(self.runtime, "runtime")
        if not isinstance(self.capability_mode, CapabilityMatchMode):
            raise DomainValidationError("capability_mode must be CapabilityMatchMode")
        object.__setattr__(
            self, "required_capabilities",
            _validate_required(self.required_capabilities, "required_capabilities"),
        )
        _validate_modalities(self.required_input_modalities, "required_input_modalities")
        _validate_modalities(self.required_output_modalities, "required_output_modalities")

    def __call__(self, deployment: Deployment) -> bool:
        if not isinstance(deployment, Deployment):
            raise DomainValidationError("DeploymentQuery requires Deployment")
        if self.deployment_id is not None and deployment.id != self.deployment_id:
            return False
        if self.model_id is not None and deployment.model_id != self.model_id:
            return False
        if self.provider_id is not None and deployment.provider_id != self.provider_id:
            return False
        if self.status is not None and deployment.status is not self.status:
            return False
        if self.region is not None and deployment.region != self.region:
            return False
        if self.runtime is not None and deployment.runtime != self.runtime:
            return False
        return _match_capabilities(
            deployment.capabilities, self.required_capabilities, self.capability_mode
        ) and _match_modalities(
            deployment.modalities,
            self.required_input_modalities,
            self.required_output_modalities,
        )
