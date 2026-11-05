"""Ports for offline canonical catalog storage and discovery (ADR-041/046/047)."""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelId
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry.discovery import DiscoveryResult
from pyllmkit.domain.registry.merge import RegistrySnapshot


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


@runtime_checkable
class DiscoverySourcePort(Protocol):
    """Pull already supplied offline candidates without writing a catalog."""

    def discover(self) -> DiscoveryResult: ...


@runtime_checkable
class AtomicCatalogPort(Protocol):
    """Snapshot/CAS contract for one in-process catalog's coordinated merge."""

    def snapshot(self) -> RegistrySnapshot: ...

    def commit_snapshot(self, snapshot: RegistrySnapshot, *, expected_revision: int) -> None: ...
