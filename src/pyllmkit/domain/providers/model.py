"""Pure provider identity and metadata: no SDK, adapter, credentials or I/O."""

from dataclasses import dataclass, replace
from typing import Self

from pyllmkit.domain.capabilities import CapabilitySet
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import ModalitySet
from pyllmkit.domain.models import ModelLimits


@dataclass(frozen=True, slots=True, order=True)
class ProviderId:
    """Provider canonical ID; opaque, stable and never normalized silently."""

    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or not self.value.strip():
            raise DomainValidationError("ProviderId must be a nonblank string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True, eq=False)
class InferenceProvider:
    """Metadata snapshot of an inference provider, not an executable adapter.

    Entity identity follows ProviderId. Changes to declarations produce a new
    snapshot via explicit replacement; None means unknown, not unsupported.
    """

    id: ProviderId
    display_name: str
    capabilities: CapabilitySet | None = None
    modalities: ModalitySet | None = None
    limits: ModelLimits | None = None

    __hash__ = None  # type: ignore[assignment]  # Domain entities are unhashable.

    def __post_init__(self) -> None:
        if not isinstance(self.id, ProviderId):
            raise DomainValidationError("InferenceProvider.id must be ProviderId")
        if type(self.display_name) is not str or not self.display_name.strip():
            raise DomainValidationError("display_name must be a nonblank string")
        if self.capabilities is not None and not isinstance(self.capabilities, CapabilitySet):
            raise DomainValidationError("capabilities must be CapabilitySet or None")
        if self.modalities is not None and not isinstance(self.modalities, ModalitySet):
            raise DomainValidationError("modalities must be ModalitySet or None")
        if self.limits is not None and not isinstance(self.limits, ModelLimits):
            raise DomainValidationError("limits must be ModelLimits or None")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InferenceProvider) and self.id == other.id

    def with_capabilities(self, capabilities: CapabilitySet | None) -> Self:
        """Return a new descriptive snapshot with the same ProviderId."""
        return replace(self, capabilities=capabilities)
