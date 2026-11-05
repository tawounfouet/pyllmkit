"""P6-AC-009..016: deterministic in-memory storage and referential integrity."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    RegistryConflictError,
    RegistryReferenceError,
    RegistryReferenceInUseError,
)
from pyllmkit.protocols import DeploymentRegistryPort, ModelRegistryPort, ProviderCatalogPort


def _model(name: str, *, context_window: int | None = None) -> Model:
    return Model(
        id=ModelId(name),
        identity=ModelIdentity(ModelFamily("llama")),
        limits=ModelLimits(context_window=context_window),
    )


def _provider(name: str) -> InferenceProvider:
    return InferenceProvider(ProviderId(name), name)


def _deployment(
    name: str, *, model: str = "m", provider: str | None = "p"
) -> Deployment:
    return Deployment(
        DeploymentId(name), ModelId(model),
        ProviderId(provider) if provider is not None else None,
    )


def test_ac009_model_registry_implements_port_with_exact_lookup() -> None:
    catalog = InMemoryCatalog()
    assert isinstance(catalog.models, ModelRegistryPort)
    assert catalog.models.get(ModelId("absent")) is None
    model = _model("m")
    catalog.models.register(model)
    assert catalog.models.get(ModelId("m")) is model
    assert catalog.models.find() == (model,)
    assert catalog.models.list() == (model,)
    assert catalog.models.remove(ModelId("absent")) is False


def test_ac010_deployment_registry_enforces_existing_typed_references() -> None:
    catalog = InMemoryCatalog()
    assert isinstance(catalog.deployments, DeploymentRegistryPort)
    with pytest.raises(RegistryReferenceError, match="ModelId"):
        catalog.deployments.register(_deployment("d"))
    catalog.models.register(_model("m"))
    with pytest.raises(RegistryReferenceError, match="ProviderId"):
        catalog.deployments.register(_deployment("d"))
    catalog.providers.register(_provider("p"))
    dep = _deployment("d")
    catalog.deployments.register(dep)
    assert catalog.deployments.get(DeploymentId("d")) is dep
    assert catalog.deployments.get(DeploymentId("missing")) is None
    assert catalog.deployments.remove(DeploymentId("nope")) is False


def test_ac010_local_deployment_does_not_invent_provider() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    local = _deployment("local", provider=None)
    catalog.deployments.register(local)
    assert catalog.providers.list() == ()
    assert catalog.deployments.get(local.id) is local


def test_ac011_provider_catalog_is_metadata_only_and_separate_port() -> None:
    catalog = InMemoryCatalog()
    assert isinstance(catalog.providers, ProviderCatalogPort)
    assert not isinstance(catalog.providers, DeploymentRegistryPort)
    assert catalog.providers.get(ProviderId("none")) is None
    catalog.providers.register(_provider("p"))
    assert catalog.providers.get(ProviderId("p")) == _provider("p")
    assert not hasattr(catalog.providers, "adapter_factory")
    assert not hasattr(catalog.providers, "client")
    assert catalog.providers.remove(ProviderId("none")) is False


def test_ac012_idempotent_register_preserves_original_snapshot_object() -> None:
    catalog = InMemoryCatalog()
    model = _model("m")
    provider = _provider("p")
    deployment = _deployment("d")
    catalog.models.register(model)
    catalog.providers.register(provider)
    catalog.deployments.register(deployment)
    catalog.models.register(_model("m"))
    catalog.providers.register(_provider("p"))
    catalog.deployments.register(_deployment("d"))
    assert catalog.models.get(ModelId("m")) is model
    assert catalog.providers.get(ProviderId("p")) is provider
    assert catalog.deployments.get(DeploymentId("d")) is deployment
    assert len(catalog.models.list()) == len(catalog.providers.list()) == 1
    assert len(catalog.deployments.list()) == 1


def test_ac013_model_collision_checks_all_metadata_not_identity_only() -> None:
    catalog = InMemoryCatalog()
    first = _model("m", context_window=1024)
    second = _model("m", context_window=2048)
    assert first == second  # Model.__eq__ intentionally uses ModelId only
    catalog.models.register(first)
    with pytest.raises(RegistryConflictError, match="ModelId"):
        catalog.models.register(second)
    assert catalog.models.get(ModelId("m")) is first


def test_ac013_provider_and_deployment_collision_cannot_overwrite() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.providers.register(_provider("p"))
    dep = _deployment("d")
    catalog.deployments.register(dep)
    with pytest.raises(RegistryConflictError, match="ProviderId"):
        catalog.providers.register(InferenceProvider(ProviderId("p"), "changed"))
    with pytest.raises(RegistryConflictError, match="DeploymentId"):
        catalog.deployments.register(dep.with_status(DeploymentStatus.AVAILABLE))
    assert catalog.deployments.get(dep.id) is dep
    assert catalog.providers.get(ProviderId("p")) == _provider("p")


def test_ac014_referenced_model_and_provider_cannot_be_removed() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.providers.register(_provider("p"))
    catalog.deployments.register(_deployment("d"))
    with pytest.raises(RegistryReferenceInUseError, match="Model"):
        catalog.models.remove(ModelId("m"))
    with pytest.raises(RegistryReferenceInUseError, match="Provider"):
        catalog.providers.remove(ProviderId("p"))
    assert len(catalog.deployments.list()) == 1
    assert catalog.deployments.remove(DeploymentId("d")) is True
    assert catalog.models.remove(ModelId("m")) is True
    assert catalog.providers.remove(ProviderId("p")) is True


def test_ac015_all_three_registries_return_sorted_tuple_not_insertion_order() -> None:
    catalog = InMemoryCatalog()
    for model_id in ("z", "a", "m"):
        catalog.models.register(_model(model_id))
    for provider_id in ("p-z", "p-a", "p-m"):
        catalog.providers.register(_provider(provider_id))
    for id_ in ("dep-z", "dep-a", "dep-m"):
        catalog.deployments.register(_deployment(id_, model="a", provider="p-a"))
    assert tuple(m.id.value for m in catalog.models.list()) == ("a", "m", "z")
    assert tuple(p.id.value for p in catalog.providers.list()) == ("p-a", "p-m", "p-z")
    assert tuple(d.id.value for d in catalog.deployments.list()) == (
        "dep-a", "dep-m", "dep-z"
    )
    assert isinstance(catalog.models.list(), tuple)
    assert isinstance(catalog.providers.list(), tuple)
    assert isinstance(catalog.deployments.list(), tuple)


def test_ac016_snapshot_and_find_results_are_immutable_and_no_dict_is_exposed() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("a"))
    catalog.models.register(_model("b"))
    found = catalog.models.find(lambda m: m.id.value == "b")
    assert tuple(m.id.value for m in found) == ("b",)
    assert not isinstance(found, dict)
    assert not isinstance(catalog.models.list(), dict)
    assert not hasattr(catalog.models, "data")
    with pytest.raises(FrozenInstanceError):
        found[0].limits = None  # type: ignore[misc]
    with pytest.raises(TypeError):
        found[0] = _model("mutated")  # type: ignore[index]
    assert catalog.models.get(ModelId("b")) is found[0]


def test_find_is_strict_bool_and_predicate_results_preserve_order() -> None:
    catalog = InMemoryCatalog()
    for item in ("z", "a", "b"):
        catalog.models.register(_model(item))
    assert tuple(m.id.value for m in catalog.models.find(lambda m: m.id.value != "b")) == (
        "a", "z"
    )
    with pytest.raises(DomainValidationError, match="callable"):
        catalog.models.find(cast(object, "not callable"))  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError, match="bool"):
        catalog.models.find(lambda _: cast(bool, None))


def test_other_registry_find_filters_without_mutating_originals() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.providers.register(_provider("p"))
    catalog.providers.register(_provider("q"))
    for id_ in ("d2", "d1"):
        catalog.deployments.register(_deployment(id_))
    assert tuple(p.id.value for p in catalog.providers.find(lambda p: p.id.value == "q")) == (
        "q",
    )
    assert tuple(d.id.value for d in catalog.deployments.find(lambda d: True)) == (
        "d1", "d2"
    )
    assert len(catalog.models.list()) == 1
    assert len(catalog.deployments.list()) == 2


def test_all_port_operations_reject_wrong_identifier_or_entity_type() -> None:
    catalog = InMemoryCatalog()
    with pytest.raises(DomainValidationError):
        catalog.models.register(cast(Model, "wrong"))
    with pytest.raises(DomainValidationError):
        catalog.providers.register(cast(InferenceProvider, "wrong"))
    with pytest.raises(DomainValidationError):
        catalog.deployments.register(cast(Deployment, "wrong"))
    for action in (
        lambda: catalog.models.get(cast(ModelId, "wrong")),
        lambda: catalog.models.remove(cast(ModelId, "wrong")),
        lambda: catalog.providers.get(cast(ProviderId, "wrong")),
        lambda: catalog.providers.remove(cast(ProviderId, "wrong")),
        lambda: catalog.deployments.get(cast(DeploymentId, "wrong")),
        lambda: catalog.deployments.remove(cast(DeploymentId, "wrong")),
    ):
        with pytest.raises(DomainValidationError):
            action()
