"""ADR-015: passive, typed, immutable inference targets."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError, ModelId
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    ModelTarget,
)


def test_three_disjoint_target_variants_are_value_objects() -> None:
    model = ModelTarget(ModelId("model/family"))
    deployed = DeploymentTarget(DeploymentId("deployment-1"))
    endpoint = EndpointTarget(EndpointId("endpoint-1"))
    assert [model.kind, deployed.kind, endpoint.kind] == ["model", "deployment", "endpoint"]
    assert model == ModelTarget(ModelId("model/family"))
    assert hash(model) == hash(ModelTarget(ModelId("model/family")))
    assert deployed == DeploymentTarget(DeploymentId("deployment-1"))
    assert endpoint == EndpointTarget(EndpointId("endpoint-1"))
    assert model != deployed
    assert deployed != endpoint
    assert model.model_id.value == "model/family"
    assert str(deployed.deployment_id) == "deployment-1"
    assert str(endpoint.endpoint_id) == "endpoint-1"


@pytest.mark.parametrize("bad", ["", " \t", None, 2, True, {}])
def test_opaque_ids_reject_blank_and_nonstring(bad: object) -> None:
    for cls in (DeploymentId, EndpointId):
        with pytest.raises(DomainValidationError):
            cls(cast(str, bad))


def test_identifiers_preserve_exact_unmodified_text() -> None:
    assert DeploymentId(" deploy- 01 ").value == " deploy- 01 "
    assert EndpointId("endpoint://opaque-key").value == "endpoint://opaque-key"


def test_cross_type_identifier_rejected_without_coercion() -> None:
    with pytest.raises(DomainValidationError, match="model_id"):
        ModelTarget(cast(ModelId, DeploymentId("x")))
    with pytest.raises(DomainValidationError, match="deployment_id"):
        DeploymentTarget(cast(DeploymentId, ModelId("x")))
    with pytest.raises(DomainValidationError, match="endpoint_id"):
        EndpointTarget(cast(EndpointId, DeploymentId("x")))
    with pytest.raises(DomainValidationError):
        EndpointTarget(cast(EndpointId, "http://example.invalid"))


def test_targets_and_identifiers_are_immutable() -> None:
    target = DeploymentTarget(DeploymentId("dep1"))
    with pytest.raises(FrozenInstanceError):
        target.deployment_id = DeploymentId("changed")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        target.deployment_id.value = "changed"  # type: ignore[misc]
