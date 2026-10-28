"""Model catalog JSON round-trip and schema-loss prevention."""

import json

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
    artifact_from_dict,
    artifact_to_dict,
    model_from_dict,
    model_to_dict,
)


def example_model() -> Model:
    model_id = ModelId("meta/llama/3.1/70b")
    return Model(
        id=model_id,
        identity=ModelIdentity(
            family=ModelFamily("llama"),
            version=ModelVersion("2026-10"),
            variant=ModelVariant("70b"),
            revision=ModelRevision("snap1"),
            developer="Meta",
            specialization="instruct",
        ),
        architecture=ModelArchitecture(parameter_count=70_000_000_000),
        limits=ModelLimits(context_window=128000),
        provider_refs=(ProviderModelRef("host", model_id, "llama-hosted"),),
    )


def test_model_round_trip_preserves_all_known_fields() -> None:
    first = example_model()
    encoded = model_to_dict(first)
    decoded = model_from_dict(json.loads(json.dumps(encoded)))
    assert model_to_dict(decoded) == encoded
    assert decoded.identity == first.identity
    assert decoded.limits == first.limits
    assert decoded.provider_refs == first.provider_refs


def test_model_round_trip_preserves_unknown_optional_values_as_none() -> None:
    original = Model(ModelId("unknown"), ModelIdentity(ModelFamily("family")))
    decoded = model_from_dict(json.loads(json.dumps(model_to_dict(original))))
    assert decoded.architecture is None
    assert decoded.identity.version is None
    assert decoded.limits is None


def test_artifact_round_trip_and_association() -> None:
    artifact = ModelArtifact(
        id=ModelArtifactId("gguf-q4"),
        model_id=example_model().id,
        format="GGUF",
        precision="int4",
        quantization="Q4_K_M",
        size_bytes=11,
        revision=ModelRevision("rev"),
    )
    assert artifact_to_dict(
        artifact_from_dict(json.loads(json.dumps(artifact_to_dict(artifact))))
    ) == artifact_to_dict(artifact)


def test_unknown_schema_keys_are_rejected_not_silently_dropped() -> None:
    doc = model_to_dict(example_model())
    doc["unexpected_provider_blob"] = {"something": "else"}
    with pytest.raises(DomainValidationError, match="unknown model keys"):
        model_from_dict(doc)


@pytest.mark.parametrize("version", [None, True, 0, 2, "1"])
def test_invalid_schema_version_is_rejected(version: object) -> None:
    doc = model_to_dict(example_model())
    doc["schema_version"] = version
    with pytest.raises(DomainValidationError, match="schema_version"):
        model_from_dict(doc)


def test_provider_alias_model_id_mismatch_is_rejected() -> None:
    doc = model_to_dict(example_model())
    refs = doc["provider_refs"]
    assert isinstance(refs, list)
    refs[0]["model_id"] = "not-the-model"
    with pytest.raises(DomainValidationError, match="reference"):
        model_from_dict(doc)


def test_artifact_unknown_version_rejected() -> None:
    doc = artifact_to_dict(ModelArtifact(ModelArtifactId("a"), ModelId("m"), "GGUF"))
    doc["schema_version"] = 9
    with pytest.raises(DomainValidationError):
        artifact_from_dict(doc)
