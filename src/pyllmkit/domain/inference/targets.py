"""Typed, passive inference targets (ADR-015, P3-L3.1).

Targets describe intent only; they do not resolve providers, endpoints or credentials.
"""

from dataclasses import dataclass
from typing import Literal

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.models import ModelId


def _require_identifier(value: str, label: str) -> None:
    if type(value) is not str or not value.strip():
        raise DomainValidationError(f"{label} must be a nonblank string")


@dataclass(frozen=True, slots=True)
class DeploymentId:
    """Opaque Serving identifier, distinct from ModelId and EndpointId."""

    value: str

    def __post_init__(self) -> None:
        _require_identifier(self.value, "DeploymentId")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class EndpointId:
    """Opaque endpoint identity, never an URL to fetch or a credential."""

    value: str

    def __post_init__(self) -> None:
        _require_identifier(self.value, "EndpointId")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ModelTarget:
    """Reference an existing logical ModelId without resolving it."""

    model_id: ModelId

    def __post_init__(self) -> None:
        if type(self.model_id) is not ModelId:
            raise DomainValidationError("ModelTarget.model_id must be ModelId")

    @property
    def kind(self) -> Literal["model"]:
        return "model"


@dataclass(frozen=True, slots=True)
class DeploymentTarget:
    """Reference a deployment by typed opaque identity."""

    deployment_id: DeploymentId

    def __post_init__(self) -> None:
        if type(self.deployment_id) is not DeploymentId:
            raise DomainValidationError("DeploymentTarget.deployment_id must be DeploymentId")

    @property
    def kind(self) -> Literal["deployment"]:
        return "deployment"


@dataclass(frozen=True, slots=True)
class EndpointTarget:
    """Reference an endpoint by typed identity without network access."""

    endpoint_id: EndpointId

    def __post_init__(self) -> None:
        if type(self.endpoint_id) is not EndpointId:
            raise DomainValidationError("EndpointTarget.endpoint_id must be EndpointId")

    @property
    def kind(self) -> Literal["endpoint"]:
        return "endpoint"


InferenceTarget = ModelTarget | DeploymentTarget | EndpointTarget
