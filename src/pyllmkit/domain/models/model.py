"""Logical Model Entity and provider alias Value Object."""

from dataclasses import dataclass, replace
from typing import Self

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

    Capabilities and modalities are intentionally deferred to L1.2.
    ModelArtifact remains a distinct Entity referenced by ModelId.
    """

    id: ModelId
    identity: ModelIdentity
    architecture: ModelArchitecture | None = None
    limits: ModelLimits | None = None
    provider_refs: tuple[ProviderModelRef, ...] = ()

    __hash__ = None

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

    def with_limits(self, limits: ModelLimits | None) -> Self:
        """Replace documented limits without changing identity."""
        return replace(self, limits=limits)
