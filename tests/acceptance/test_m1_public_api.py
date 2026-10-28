"""M1 public-domain import contract and version-one serialization policy."""

import json

import pytest

from pyllmkit.domain import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    DomainValidationError,
    Model,
    ModelArtifact,
    ModelArtifactId,
    ModelFamily,
    ModelId,
    ModelIdentity,
    Modality,
    ModalitySet,
    SupportLevel,
    model_from_dict,
    model_to_dict,
)
from pyllmkit.domain.models import Model as ModelFromSubpackage


def test_public_domain_import_alias_matches_subpackage() -> None:
    assert Model is ModelFromSubpackage
    assert ModelId("alpha") != ModelArtifactId("alpha")


def test_public_domain_api_without_provider_runtime() -> None:
    model = Model(
        id=ModelId("model-one"),
        identity=ModelIdentity(ModelFamily("example")),
        capabilities=CapabilitySet(
            (Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),)
        ),
        modalities=ModalitySet(input_modalities=frozenset({Modality("image")})),
    )
    artifact = ModelArtifact(ModelArtifactId("weights-a"), model.id, "GGUF")
    assert artifact.model_id == model.id
    assert model.supports(CapabilityId("vision"))
    assert model.modalities.accepts_input(Modality("image")) is True


def test_schema_v1_alpha_roundtrip() -> None:
    model = Model(
        id=ModelId("alpha"),
        identity=ModelIdentity(ModelFamily("example")),
    )
    raw = json.loads(json.dumps(model_to_dict(model)))
    assert raw["schema_version"] == 1
    assert model_to_dict(model_from_dict(raw)) == raw


def test_old_v1_document_readable_but_old_strict_reader_not_promised() -> None:
    model = Model(ModelId("alpha"), ModelIdentity(ModelFamily("example")))
    old_v1 = model_to_dict(model)
    del old_v1["capabilities"]
    del old_v1["modalities"]
    parsed = model_from_dict(old_v1)
    assert parsed.capabilities == CapabilitySet()
    assert parsed.modalities == ModalitySet()


def test_future_schema_requires_explicit_version_and_migration() -> None:
    model = Model(ModelId("alpha"), ModelIdentity(ModelFamily("example")))
    data = model_to_dict(model)
    data["schema_version"] = 2
    with pytest.raises(DomainValidationError, match="schema_version"):
        model_from_dict(data)


def test_unknown_fields_are_not_silently_dropped() -> None:
    model = Model(ModelId("alpha"), ModelIdentity(ModelFamily("example")))
    data = model_to_dict(model)
    data["provider_native_response"] = {"unexpected": True}
    with pytest.raises(DomainValidationError, match="unknown model keys"):
        model_from_dict(data)
