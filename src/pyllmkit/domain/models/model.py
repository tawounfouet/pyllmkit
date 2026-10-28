"""Logical Model Entity and provider alias Value Object."""

from dataclasses import dataclass, field, replace
from typing import Self

from pyllmkit.domain.capabilities import CapabilityId, CapabilitySet
from pyllmkit.domain.modalities import ModalitySet
from pyllmkit.domain.errors import DomainValidationError

from .descriptors import ModelArchitecture, ModelLimits
from .identifiers import ModelId, require_nonblank
from .identity import ModelIdentity


@dataclass(frozen=True, slots=True)
class ProviderModelRef:
    """Optional external alias; never replaces ModelId (MODEL-003)."""

    provider_id: str
    model_id: ModelId
    provider_model_name: str
    api_version: str | None = None

    def __post_init__(self) -> None:
        require_nonblank(self.provider_id, "provider_id")
        require_nonblank(self.provider_model_name, "provider_model_name")
        if not isinstance(self.model_id, ModelId):
            raise DomainValidationError("model_id must be ModelId")
        if self.api_version is not None:
            require_nonblank(self.api_version, "api_version")


@dataclass(frozen=True, slots=True, eq=False)
class Model:
    """Aggregate Root; equality follows ModelId, not metadata snapshots.

    Intrinsic capabilities and modalities are composed in L1.2.
    ModelArtifact remains a distinct Entity referenced by ModelId.
    """

    id: ModelId
    identity: ModelIdentity
    architecture: ModelArchitecture | None = None
    limits: ModelLimits | None = None
    provider_refs: tuple[ProviderModelRef, ...] = ()
    capabilities: CapabilitySet = field(default_factory=CapabilitySet)
    modalities: ModalitySet = field(default_factory=ModalitySet)

    __hash__ = None  # type: ignore[assignment]  # Entities are unhashable

    def __post_init__(self) -> None:
        if not isinstance(self.id, ModelId):
            raise DomainValidationError("id must be ModelId")
        if not isinstance(self.identity, ModelIdentity):
            raise DomainValidationError("identity must be ModelIdentity")
        if self.architecture is not None and not isinstance(
            self.architecture, ModelArchitecture
        ):
            raise DomainValidationError("architecture must be ModelArchitecture or None")
        if self.limits is not None and not isinstance(self.limits, ModelLimits):
            raise DomainValidationError("limits must be ModelLimits or None")
        if not isinstance(self.capabilities, CapabilitySet):
            raise DomainValidationError("capabilities must be CapabilitySet")
        if not isinstance(self.modalities, ModalitySet):
            raise DomainValidationError("modalities must be ModalitySet")
        if not isinstance(self.provider_refs, tuple):
            raise DomainValidationError("provider_refs must be immutable tuple")
        for alias in self.provider_refs:
            if not isinstance(alias, ProviderModelRef) or alias.model_id != self.id:
                raise DomainValidationError("provider_refs must reference this ModelId")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Model) and self.id == other.id

    def with_identity(self, identity: ModelIdentity) -> Self:
        """Return another snapshot of the same logical Entity."""
        return replace(self, identity=identity)

    def supports(self, capability_id: CapabilityId) -> bool:
        """Query intrinsic declared support, not effective provider support."""
        return self.capabilities.supports(capability_id)

    def with_capabilities(self, capabilities: CapabilitySet) -> Self:
        """Return a new snapshot with different intrinsic capabilities."""
        return replace(self, capabilities=capabilities)

    def with_modalities(self, modalities: ModalitySet) -> Self:
        """Return a new snapshot with different directional modalities."""
        return replace(self, modalities=modalities)

    def with_limits(self, limits: ModelLimits | None) -> Self:
        """Replace documented limits without changing identity."""
        return replace(self, limits=limits)
