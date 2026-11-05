"""Pure in-memory registry ports with one replaceable catalog snapshot.

Regular port writes and coordinated import commits replace a single shared
state reference (copy-on-write). This is an in-process sequential/CAS contract,
not distributed persistence or a cross-process transaction.
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
    CatalogProvenance,
    RegistryConflictError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
    RegistrySnapshot,
    RegistryStaleSnapshotError,
)

_T = TypeVar("_T")


def _same_complete_snapshot(
    left: Model | InferenceProvider | Deployment,
    right: Model | InferenceProvider | Deployment,
) -> bool:
    """Entity equality follows identity; metadata comparison inspects every field."""
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


@dataclass(frozen=True, slots=True)
class _CatalogData:
    """Private committed state. Never mutate dictionaries after publication."""

    models: dict[ModelId, Model] = field(default_factory=dict)
    providers: dict[ProviderId, InferenceProvider] = field(default_factory=dict)
    deployments: dict[DeploymentId, Deployment] = field(default_factory=dict)
    provenance: dict[tuple[str, str], CatalogProvenance] = field(default_factory=dict)
    revision: int = 0


class _CatalogState:
    """One shared pointer used by all ports, replaced after complete validation."""

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data = _CatalogData()

    @property
    def models(self) -> dict[ModelId, Model]:
        return self._data.models

    @property
    def providers(self) -> dict[ProviderId, InferenceProvider]:
        return self._data.providers

    @property
    def deployments(self) -> dict[DeploymentId, Deployment]:
        return self._data.deployments

    @property
    def provenance(self) -> dict[tuple[str, str], CatalogProvenance]:
        return self._data.provenance

    @property
    def revision(self) -> int:
        return self._data.revision

    def publish(
        self,
        *,
        models: dict[ModelId, Model] | None = None,
        providers: dict[ProviderId, InferenceProvider] | None = None,
        deployments: dict[DeploymentId, Deployment] | None = None,
        provenance: dict[tuple[str, str], CatalogProvenance] | None = None,
    ) -> None:
        """Commit one new root pointer; unchanged maps are never mutated."""
        old = self._data
        self._data = _CatalogData(
            models=old.models if models is None else models,
            providers=old.providers if providers is None else providers,
            deployments=old.deployments if deployments is None else deployments,
            provenance=old.provenance if provenance is None else provenance,
            revision=old.revision + 1,
        )


class InMemoryModelRegistry:
    """One model port, backed by the Catalog-owned shared state."""

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
        values = dict(self._state.models)
        values[model.id] = model
        self._state.publish(models=values)

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
        values = dict(self._state.models)
        del values[model_id]
        provenance = dict(self._state.provenance)
        provenance.pop(("model", model_id.value), None)
        self._state.publish(models=values, provenance=provenance)
        return True


class InMemoryProviderCatalog:
    """Metadata catalog only; no provider SDK, executable adapter or secrets."""

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
        values = dict(self._state.providers)
        values[provider.id] = provider
        self._state.publish(providers=values)

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
        values = dict(self._state.providers)
        del values[provider_id]
        provenance = dict(self._state.provenance)
        provenance.pop(("provider", provider_id.value), None)
        self._state.publish(providers=values, provenance=provenance)
        return True


class InMemoryDeploymentRegistry:
    """Deployment metadata with strict Model and optional Provider references."""

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
        values = dict(self._state.deployments)
        values[deployment.id] = deployment
        self._state.publish(deployments=values)

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
        values = dict(self._state.deployments)
        del values[deployment_id]
        provenance = dict(self._state.provenance)
        provenance.pop(("deployment", deployment_id.value), None)
        self._state.publish(deployments=values, provenance=provenance)
        return True


class InMemoryCatalog:
    """Three registry ports over one revisioned snapshot root.

    A coordinated merge calls snapshot(), validates a *candidate copy*, then
    commit_snapshot() with an exact revision lease. Snapshot swaps are atomic
    within this single in-process sequential catalog. No external storage,
    distributed transaction or cross-thread isolation is promised.
    """

    __slots__ = ("_state", "models", "providers", "deployments")

    def __init__(self) -> None:
        state = _CatalogState()
        self._state = state
        self.models = InMemoryModelRegistry(state)
        self.providers = InMemoryProviderCatalog(state)
        self.deployments = InMemoryDeploymentRegistry(state)

    def snapshot(self) -> RegistrySnapshot:
        """Copy canonical immutable record tuples, provenance and revision."""
        state = self._state
        return RegistrySnapshot(
            revision=state.revision,
            models=self.models.list(),
            providers=self.providers.list(),
            deployments=self.deployments.list(),
            provenance=tuple(
                state.provenance[key] for key in sorted(state.provenance)
            ),
        )

    def commit_snapshot(self, snapshot: RegistrySnapshot, *, expected_revision: int) -> None:
        """CAS write of a fully validated candidate, with one shared-pointer swap."""
        if not isinstance(snapshot, RegistrySnapshot):
            raise DomainValidationError("expected RegistrySnapshot")
        if type(expected_revision) is not int or expected_revision < 0:
            raise DomainValidationError("expected_revision must be nonnegative int")
        if self._state.revision != expected_revision:
            raise RegistryStaleSnapshotError("Catalog changed after preview")
        if snapshot.revision != expected_revision:
            raise RegistryStaleSnapshotError("Candidate was built from a stale revision")
        models = {model.id: model for model in snapshot.models}
        providers = {provider.id: provider for provider in snapshot.providers}
        deployments = {dep.id: dep for dep in snapshot.deployments}
        for dep in deployments.values():
            if dep.model_id not in models or (
                dep.provider_id is not None and dep.provider_id not in providers
            ):
                raise RegistryReferenceError("Candidate deployment has missing references")
        provenance = {
            (entry.entity_type, entry.entity_id): entry for entry in snapshot.provenance
        }
        for kind, ident in provenance:
            valid = (
                (kind == "model" and ModelId(ident) in models)
                or (kind == "provider" and ProviderId(ident) in providers)
                or (kind == "deployment" and DeploymentId(ident) in deployments)
            )
            if not valid:
                raise RegistryReferenceError("Candidate provenance refers to missing record")
        self._state.publish(
            models=models,
            providers=providers,
            deployments=deployments,
            provenance=provenance,
        )
