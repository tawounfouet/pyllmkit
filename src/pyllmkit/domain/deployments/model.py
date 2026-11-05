"""Passive deployment snapshots with an explicit descriptive status lifecycle."""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Self

from pyllmkit.domain.capabilities import CapabilitySet
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference.targets import DeploymentId
from pyllmkit.domain.modalities import ModalitySet
from pyllmkit.domain.models import ModelId, ModelLimits
from pyllmkit.domain.providers import ProviderId


class DeploymentStatus(StrEnum):
    """Catalog-declared status, never proof of live service availability."""

    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True, eq=False)
class Deployment:
    """Logical metadata about one serving exposure of one existing ModelId.

    A missing ProviderId is valid for a local runtime; this entity does not
    create or probe any provider, physical endpoint or inference connection.
    """

    id: DeploymentId
    model_id: ModelId
    provider_id: ProviderId | None = None
    status: DeploymentStatus = DeploymentStatus.UNKNOWN
    capabilities: CapabilitySet | None = None
    modalities: ModalitySet | None = None
    limits: ModelLimits | None = None
    region: str | None = None
    runtime: str | None = None

    __hash__ = None  # type: ignore[assignment]  # Identity-based domain entity.

    def __post_init__(self) -> None:
        if not isinstance(self.id, DeploymentId):
            raise DomainValidationError("Deployment.id must be DeploymentId")
        if not isinstance(self.model_id, ModelId):
            raise DomainValidationError("Deployment.model_id must be ModelId")
        if self.provider_id is not None and not isinstance(self.provider_id, ProviderId):
            raise DomainValidationError("provider_id must be ProviderId or None")
        if not isinstance(self.status, DeploymentStatus):
            raise DomainValidationError("status must be DeploymentStatus")
        if self.capabilities is not None and not isinstance(self.capabilities, CapabilitySet):
            raise DomainValidationError("capabilities must be CapabilitySet or None")
        if self.modalities is not None and not isinstance(self.modalities, ModalitySet):
            raise DomainValidationError("modalities must be ModalitySet or None")
        if self.limits is not None and not isinstance(self.limits, ModelLimits):
            raise DomainValidationError("limits must be ModelLimits or None")
        for label in ("region", "runtime"):
            value = getattr(self, label)
            if value is not None and (type(value) is not str or not value.strip()):
                raise DomainValidationError(f"{label} must be a nonblank string or None")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Deployment) and self.id == other.id

    def with_status(self, status: DeploymentStatus) -> Self:
        """Explicit catalog transition; retirement cannot silently be undone.

        AVAILABLE is a declaration, not a network healthcheck. The same
        status is an idempotent no-op, not a synthetic lifecycle transition.
        """
        if not isinstance(status, DeploymentStatus):
            raise DomainValidationError("status must be DeploymentStatus")
        if status is self.status:
            return self
        if self.status is DeploymentStatus.DEPRECATED:
            raise DomainValidationError("DEPRECATED deployment cannot be reactivated")
        return replace(self, status=status)
