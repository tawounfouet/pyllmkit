"""P6-G1 candidate - L6.1 provider and deployment domain acceptance tests.

These tests are implementation evidence on a draft branch, not a qualified gate.
"""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId, DeploymentTarget, ModelTarget
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import ModelId, ModelLimits, ProviderModelRef
from pyllmkit.domain.providers import InferenceProvider, ProviderId


def test_ac001_provider_id_is_typed_opaque_ordered_immutable() -> None:
    assert str(ProviderId("provider-a")) == "provider-a"
    assert ProviderId("a") < ProviderId("b")
    assert ProviderId(" P ") == ProviderId(" P ")
    assert ProviderId(" P ") != ProviderId("P")
    with pytest.raises(FrozenInstanceError):
        ProviderId("a").value = "b"  # type: ignore[misc]


@pytest.mark.parametrize("bad", ["", "  ", "\n", None, 42, True, {}])
def test_ac001_invalid_provider_id_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        ProviderId(cast(str, bad))


def test_ac002_provider_is_passive_with_unknown_declarations() -> None:
    provider = InferenceProvider(ProviderId("metadata-host"), "Metadata Host")
    assert provider.capabilities is None
    assert provider.modalities is None
    assert provider.limits is None
    assert not hasattr(provider, "adapter")
    assert not hasattr(provider, "api_key")
    assert not hasattr(provider, "client")


def test_ac002_provider_snapshot_is_typed_and_identity_based() -> None:
    provider = InferenceProvider(ProviderId("p1"), "Provider")
    capability_set = CapabilitySet((Capability(
        CapabilityId("tool_calling"), CapabilitySupport(SupportLevel.NATIVE)
    ),))
    updated = provider.with_capabilities(capability_set)
    assert updated is not provider
    assert updated == provider
    assert updated.capabilities == capability_set
    assert provider.capabilities is None
    with pytest.raises(TypeError):
        hash(provider)
    with pytest.raises(FrozenInstanceError):
        provider.display_name = "Mutated"  # type: ignore[misc]


@pytest.mark.parametrize("field,bad", [
    ("id", "p1"), ("display_name", ""), ("display_name", " "),
    ("capabilities", []), ("modalities", []), ("limits", {}),
])
def test_ac002_invalid_provider_snapshots_rejected(field: str, bad: object) -> None:
    kwargs: dict[str, object] = {"id": ProviderId("p1"), "display_name": "Provider"}
    kwargs[field] = bad
    with pytest.raises(DomainValidationError):
        InferenceProvider(**kwargs)  # type: ignore[arg-type]


def test_ac003_deployment_reuses_existing_id_types() -> None:
    model_id = ModelId("logical/model")
    deployment_id = DeploymentId("dep-01")
    deployment = Deployment(id=deployment_id, model_id=model_id)
    assert deployment.id is deployment_id
    assert deployment.model_id is model_id
    assert deployment.id != deployment.model_id
    assert ModelTarget(model_id).model_id is model_id
    assert DeploymentTarget(deployment_id).deployment_id is deployment_id


def test_ac004_multiple_deployments_reference_one_model() -> None:
    model_id = ModelId("logical/model")
    a = Deployment(DeploymentId("d1"), model_id, ProviderId("p1"))
    b = Deployment(DeploymentId("d2"), model_id, ProviderId("p2"))
    assert a.model_id == b.model_id
    assert a != b
    assert a != object()
    with pytest.raises(TypeError):
        hash(a)


def test_ac005_local_deployment_without_provider_is_valid() -> None:
    local = Deployment(DeploymentId("local"), ModelId("llama"), runtime="vllm")
    assert local.provider_id is None
    assert local.region is None
    assert local.status is DeploymentStatus.UNKNOWN


def test_ac006_explicit_status_transition_and_deprecated_terminal() -> None:
    current = Deployment(DeploymentId("d"), ModelId("m"))
    assert current.with_status(DeploymentStatus.UNKNOWN) is current
    available = current.with_status(DeploymentStatus.AVAILABLE)
    assert available is not current
    assert available == current
    assert current.status is DeploymentStatus.UNKNOWN
    assert available.status is DeploymentStatus.AVAILABLE
    down = available.with_status(DeploymentStatus.UNAVAILABLE)
    assert down.status is DeploymentStatus.UNAVAILABLE
    retired = down.with_status(DeploymentStatus.DEPRECATED)
    assert retired.with_status(DeploymentStatus.DEPRECATED) is retired
    with pytest.raises(DomainValidationError, match="DEPRECATED"):
        retired.with_status(DeploymentStatus.AVAILABLE)
    with pytest.raises(DomainValidationError, match="status"):
        current.with_status(cast(DeploymentStatus, "available"))


def test_ac007_snapshot_keeps_typed_metadata_and_immutable_state() -> None:
    modalities = ModalitySet(frozenset((Modality("text"),)), frozenset((Modality("text"),)))
    caps = CapabilitySet((Capability(
        CapabilityId("chat"), CapabilitySupport(SupportLevel.PARTIAL, notes="subset")
    ),))
    limits = ModelLimits(context_window=8192)
    dep = Deployment(
        DeploymentId("d"), ModelId("m"), ProviderId("p"),
        capabilities=caps, modalities=modalities, limits=limits,
        region="eu-west", runtime="vllm",
    )
    assert dep.capabilities == caps
    assert dep.modalities == modalities
    assert dep.limits is limits
    assert dep.region == "eu-west"
    with pytest.raises(FrozenInstanceError):
        dep.region = "us"  # type: ignore[misc]


@pytest.mark.parametrize("field,bad", [
    ("id", ModelId("m")), ("model_id", DeploymentId("d")),
    ("provider_id", "raw"), ("status", "available"),
    ("capabilities", []), ("modalities", []), ("limits", {}),
    ("region", ""), ("region", []), ("runtime", " "), ("runtime", []),
])
def test_ac007_invalid_deployment_snapshots_rejected(field: str, bad: object) -> None:
    kwargs: dict[str, object] = {"id": DeploymentId("d"), "model_id": ModelId("m")}
    kwargs[field] = bad
    with pytest.raises(DomainValidationError):
        Deployment(**kwargs)  # type: ignore[arg-type]


def test_ac008_provider_alias_stays_string_and_id_contract_unchanged() -> None:
    alias = ProviderModelRef("external-name", ModelId("canonical"), "vendor-name")
    assert isinstance(alias.provider_id, str)
    assert alias.provider_id == "external-name"
    assert ProviderId(alias.provider_id) != alias.provider_id
    assert DeploymentId("opaque") != ModelId("opaque")
