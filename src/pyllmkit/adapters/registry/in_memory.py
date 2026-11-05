"""Pure in-memory catalog backends with shared referential integrity.

Create InMemoryCatalog() to obtain the three distinct ports over one private
state. This preserves referential checks without circular dependencies and
keeps storage mappings private. This is *not* a distributed transaction engine.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, fields
from typing import TypeVar

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelId
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    RegistryConflictError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
)

_T = TypeVar("_T")


def _same_complete_snapshot(
    left: Model | InferenceProvider | Deployment,
    right: Model | InferenceProvider | Deployment,
) -> bool:
    """Entity equality follows ID; registry collision equality follows ALL fields."""
    return type(left) is type(right) and all(
        getattr(left, item.name) == getattr(right, item.name) for item in fields(left)
    )


def _filter(
    items: tuple[_T, ...], predicate: Callable[[_T], bool] | None
) -> tuple[_T, ...]:
    if predicate is None:
        return items
    if not callable(predicate):
        raise DomainValidationError("find predicate must be callable or None")
    selected: list[_T] = []
    for item in items:
        matches = predicate(item)
        if type(matches) is not bool:
            raise DomainValidationError("find predicate must return bool")
        if matches:
            selected.append(item)
    return tuple(selected)


@dataclass(slots=True)
class _CatalogState:
    models: dict[ModelId, Model] = field(default_factory=dict)
    providers: dict[ProviderId, InferenceProvider] = field(default_factory=dict)
    deployments: dict[DeploymentId, Deployment] = field(default_factory=dict)


class InMemoryModelRegistry:
    """One model port, backed by a Catalog-owned private state."""

    __slots__ = ("_state",)

    def __init__(self, state: _CatalogState) -> None:
        self._state = state

    def register(self, model: Model) -> None:
        if not isinstance(model, Model):
            raise DomainValidationError("register expects Model")
        existing = self._state.models.get(model.id)
        if existing is not None:
            if not _same_complete_snapshot(existing, model):
                raise RegistryConflictError("ModelId collision with different metadata")
            return
        self._state.models[model.id] = model

    def get(self, model_id: ModelId) -> Model | None:
        if not isinstance(model_id, ModelId):
            raise DomainValidationError("get expects ModelId")
        return self._state.models.get(model_id)

    def list(self) -> tuple[Model, ...]:
        return tuple(sorted(self._state.models.values(), key=lambda item: item.id.value))

    def find(self, predicate: Callable[[Model], bool] | None = None) -> tuple[Model, ...]:
        return _filter(self.list(), predicate)

    def remove(self, model_id: ModelId) -> bool:
        if not isinstance(model_id, ModelId):
            raise DomainValidationError("remove expects ModelId")
        if model_id not in self._state.models:
            return False
        if any(dep.model_id == model_id for dep in self._state.deployments.values()):
            raise RegistryReferenceInUseError("cannot remove referenced Model")
        del self._state.models[model_id]
        return True


class InMemoryProviderCatalog:
    """Metadata catalog only; no adapter registry, runtime or credentials."""

    __slots__ = ("_state",)

    def __init__(self, state: _CatalogState) -> None:
        self._state = state

    def register(self, provider: InferenceProvider) -> None:
        if not isinstance(provider, InferenceProvider):
            raise DomainValidationError("register expects InferenceProvider")
        existing = self._state.providers.get(provider.id)
        if existing is not None:
            if not _same_complete_snapshot(existing, provider):
                raise RegistryConflictError("ProviderId collision with different metadata")
            return
        self._state.providers[provider.id] = provider

    def get(self, provider_id: ProviderId) -> InferenceProvider | None:
        if not isinstance(provider_id, ProviderId):
            raise DomainValidationError("get expects ProviderId")
        return self._state.providers.get(provider_id)

    def list(self) -> tuple[InferenceProvider, ...]:
        return tuple(sorted(self._state.providers.values(), key=lambda item: item.id.value))

    def find(
        self, predicate: Callable[[InferenceProvider], bool] | None = None
    ) -> tuple[InferenceProvider, ...]:
        return _filter(self.list(), predicate)

    def remove(self, provider_id: ProviderId) -> bool:
        if not isinstance(provider_id, ProviderId):
            raise DomainValidationError("remove expects ProviderId")
        if provider_id not in self._state.providers:
            return False
        if any(dep.provider_id == provider_id for dep in self._state.deployments.values()):
            raise RegistryReferenceInUseError("cannot remove referenced Provider")
        del self._state.providers[provider_id]
        return True


class InMemoryDeploymentRegistry:
    """Deployment storage with strict Model and optional Provider references."""

    __slots__ = ("_state",)

    def __init__(self, state: _CatalogState) -> None:
        self._state = state

    def register(self, deployment: Deployment) -> None:
        if not isinstance(deployment, Deployment):
            raise DomainValidationError("register expects Deployment")
        if deployment.model_id not in self._state.models:
            raise RegistryReferenceError("Deployment references unknown ModelId")
        if (
            deployment.provider_id is not None
            and deployment.provider_id not in self._state.providers
        ):
            raise RegistryReferenceError("Deployment references unknown ProviderId")
        existing = self._state.deployments.get(deployment.id)
        if existing is not None:
            if not _same_complete_snapshot(existing, deployment):
                raise RegistryConflictError("DeploymentId collision with different metadata")
            return
        self._state.deployments[deployment.id] = deployment

    def get(self, deployment_id: DeploymentId) -> Deployment | None:
        if not isinstance(deployment_id, DeploymentId):
            raise DomainValidationError("get expects DeploymentId")
        return self._state.deployments.get(deployment_id)

    def list(self) -> tuple[Deployment, ...]:
        return tuple(sorted(self._state.deployments.values(), key=lambda item: item.id.value))

    def find(
        self, predicate: Callable[[Deployment], bool] | None = None
    ) -> tuple[Deployment, ...]:
        return _filter(self.list(), predicate)

    def remove(self, deployment_id: DeploymentId) -> bool:
        if not isinstance(deployment_id, DeploymentId):
            raise DomainValidationError("remove expects DeploymentId")
        if deployment_id not in self._state.deployments:
            return False
        del self._state.deployments[deployment_id]
        return True


class InMemoryCatalog:
    """Compose three separate registry ports over one referentially safe state.

    The bundle is the supported creation entrypoint. The mappings are private;
    callers get frozen metadata objects and immutable tuples instead of dicts.
    """

    __slots__ = ("_state", "models", "providers", "deployments")

    def __init__(self) -> None:
        state = _CatalogState()
        self._state = state
        self.models = InMemoryModelRegistry(state)
        self.providers = InMemoryProviderCatalog(state)
        self.deployments = InMemoryDeploymentRegistry(state)
