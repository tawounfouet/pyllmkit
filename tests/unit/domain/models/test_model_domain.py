"""Tests for L1.1 model domain semantics (source specs 05-07)."""

from dataclasses import FrozenInstanceError

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.models import (
    Model,
    ModelArchitecture,
    ModelArtifact,
    ModelArtifactId,
    ModelFamily,
    ModelId,
    ModelIdentity,
    ModelLimits,
    ModelRevision,
    ModelVariant,
    ModelVersion,
    ProviderModelRef,
)


def basic_identity() -> ModelIdentity:
    return ModelIdentity(family=ModelFamily("llama"), version=ModelVersion("3.1"))


@pytest.mark.parametrize("raw", ["", "  ", "\n", None, 42])
def test_blank_or_invalid_model_id_is_rejected(raw: object) -> None:
    with pytest.raises(DomainValidationError):
        ModelId(raw)  # type: ignore[arg-type]


def test_ids_are_distinct_value_objects() -> None:
    assert ModelId("abc") == ModelId("abc")
    assert ModelId("abc") != ModelId("def")
    assert ModelId("abc") != ModelArtifactId("abc")
    assert str(ModelId("logical/model")) == "logical/model"


def test_versions_do_not_require_semver() -> None:
    assert ModelVersion("2026-10").value == "2026-10"
    assert ModelVersion("opus-4").value == "opus-4"


def test_family_variant_revision_are_independent() -> None:
    left = ModelIdentity(
        family=ModelFamily("llama"),
        version=ModelVersion("3.1"),
        variant=ModelVariant("70b"),
        revision=ModelRevision("checkpoint-b"),
    )
    right = ModelIdentity(
        family=ModelFamily("llama"),
        version=ModelVersion("3.1"),
        variant=ModelVariant("8b"),
    )
    assert left != right
    assert left.family == right.family
    assert left.version == right.version
    assert left.revision != right.revision


def test_identity_is_value_based_and_immutable() -> None:
    left, right = basic_identity(), basic_identity()
    assert left == right
    with pytest.raises(FrozenInstanceError):
        left.developer = "someone"  # type: ignore[misc]


def test_identity_requires_typed_family() -> None:
    with pytest.raises(DomainValidationError):
        ModelIdentity(family="llama")  # type: ignore[arg-type]


def test_missing_architecture_and_limits_remain_unknown() -> None:
    model = Model(id=ModelId("meta/llama/3.1"), identity=basic_identity())
    assert model.architecture is None
    assert model.limits is None


def test_architecture_partial_metadata_preserved() -> None:
    arch = ModelArchitecture(parameter_count=70_000_000_000)
    assert arch.layer_count is None
    assert arch.architecture_type is None
    assert arch.mixture_of_experts is None


@pytest.mark.parametrize("limits", [-1, True, 1.5])
def test_invalid_context_window_rejected(limits: object) -> None:
    with pytest.raises(DomainValidationError):
        ModelLimits(context_window=limits)  # type: ignore[arg-type]


def test_model_identity_equality_and_snapshot_change() -> None:
    model = Model(id=ModelId("logical/x"), identity=basic_identity())
    changed = model.with_limits(ModelLimits(context_window=8192))
    assert changed is not model
    assert changed == model
    assert changed.limits is not None
    assert model.limits is None
    with pytest.raises(TypeError):
        hash(model)


def test_model_identity_not_equal_despite_same_descriptors() -> None:
    assert Model(id=ModelId("x"), identity=basic_identity()) != Model(
        id=ModelId("y"), identity=basic_identity()
    )


def test_model_and_artifact_are_distinct() -> None:
    model_id = ModelId("logical/model")
    model = Model(id=model_id, identity=basic_identity())
    a = ModelArtifact(id=ModelArtifactId("a"), model_id=model_id, format="GGUF")
    b = ModelArtifact(
        id=ModelArtifactId("b"), model_id=model_id,
        format="safetensors", precision="FP16",
    )
    assert model.id == a.model_id == b.model_id
    assert a != b
    assert a.id != b.id
    assert model != a


def test_artifact_equality_by_id_not_metadata() -> None:
    a = ModelArtifact(ModelArtifactId("a"), ModelId("x"), "GGUF")
    b = ModelArtifact(ModelArtifactId("a"), ModelId("x"), "safetensors")
    assert a == b
    with pytest.raises(TypeError):
        hash(a)


def test_invalid_artifact_data_rejected() -> None:
    with pytest.raises(DomainValidationError):
        ModelArtifact(ModelArtifactId("a"), ModelId("x"), "GGUF", size_bytes=-1)
    with pytest.raises(DomainValidationError):
        ModelArtifact(ModelArtifactId("a"), ModelId("x"), "")


def test_provider_model_alias_does_not_change_logical_id() -> None:
    model_id = ModelId("canonical/model")
    alias = ProviderModelRef("host", model_id, "host-specific-name")
    model = Model(model_id, basic_identity(), provider_refs=(alias,))
    assert model.id.value != alias.provider_model_name


def test_provider_alias_must_reference_model_id() -> None:
    alias = ProviderModelRef("host", ModelId("x"), "host-model")
    with pytest.raises(DomainValidationError):
        Model(ModelId("y"), basic_identity(), provider_refs=(alias,))


def test_model_rejects_mutable_provider_refs() -> None:
    with pytest.raises(DomainValidationError):
        Model(ModelId("x"), basic_identity(), provider_refs=[])  # type: ignore[arg-type]


def test_model_refuses_raw_untyped_id() -> None:
    with pytest.raises(DomainValidationError):
        Model("x", basic_identity())  # type: ignore[arg-type]


def test_no_deployment_or_endpoint_required() -> None:
    model = Model(ModelId("standalone"), ModelIdentity(ModelFamily("local")))
    assert model.id.value == "standalone"
    assert not hasattr(model, "deployment")
    assert not hasattr(model, "endpoint")
