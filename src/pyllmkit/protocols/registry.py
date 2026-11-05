"""Ports for offline canonical catalog storage (ADR-041, P6 L6.2).

Predicate-based find is a narrow, typed extension seam: P6 L6.3 will add
immutable ModelQuery / DeploymentQuery callable values without breaking ports.
These are structural Protocols, not executable provider-adapter registries.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelId
from pyllmkit.domain.providers import InferenceProvider, ProviderId


@runtime_checkable
class ModelRegistryPort(Protocol):
    """Canonical logical Model storage, not provider selection."""

    def register(self, model: Model) -> None: ...

    def get(self, model_id: ModelId) -> Model | None: ...

    def list(self) -> tuple[Model, ...]: ...

    def find(self, predicate: Callable[[Model], bool] | None = None) -> tuple[Model, ...]: ...

    def remove(self, model_id: ModelId) -> bool: ...


@runtime_checkable
class DeploymentRegistryPort(Protocol):
    """Descriptive Deployment metadata, never an endpoint or live healthcheck."""

    def register(self, deployment: Deployment) -> None: ...

    def get(self, deployment_id: DeploymentId) -> Deployment | None: ...

    def list(self) -> tuple[Deployment, ...]: ...

    def find(
        self, predicate: Callable[[Deployment], bool] | None = None
    ) -> tuple[Deployment, ...]: ...

    def remove(self, deployment_id: DeploymentId) -> bool: ...


@runtime_checkable
class ProviderCatalogPort(Protocol):
    """Descriptive provider catalog: never factories, SDKs, clients or secrets."""

    def register(self, provider: InferenceProvider) -> None: ...

    def get(self, provider_id: ProviderId) -> InferenceProvider | None: ...

    def list(self) -> tuple[InferenceProvider, ...]: ...

    def find(
        self, predicate: Callable[[InferenceProvider], bool] | None = None
    ) -> tuple[InferenceProvider, ...]: ...

    def remove(self, provider_id: ProviderId) -> bool: ...
