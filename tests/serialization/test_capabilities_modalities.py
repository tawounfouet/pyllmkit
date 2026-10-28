"""Backward compatibility and JSON schema-v1 roundtrips for L1.2."""

import json

import pytest

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityConstraint,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import (
    Model,
    ModelFamily,
    ModelId,
    ModelIdentity,
    model_from_dict,
    model_to_dict,
)


def model_with_support() -> Model:
    return Model(
        id=ModelId("example/vision"),
        identity=ModelIdentity(family=ModelFamily("example")),
        capabilities=CapabilitySet((
            Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),
            Capability(
                CapabilityId("tool_calling"),
                CapabilitySupport(
                    SupportLevel.PARTIAL,
                    constraints=(
                        CapabilityConstraint("max_tools", 1),
                        CapabilityConstraint("parallel_calls", False),
                        CapabilityConstraint("formats", ("json", "text")),
                    ),
                ),
            ),
            Capability(CapabilityId("structured_output"), CapabilitySupport()),
        )),
        modalities=ModalitySet(
            input_modalities=frozenset({Modality("text"), Modality("image")}),
            output_modalities=frozenset({Modality("text")}),
        ),
    )


def test_composed_model_roundtrip_json() -> None:
    model = model_with_support()
    encoded = model_to_dict(model)
    decoded = model_from_dict(json.loads(json.dumps(encoded)))
    assert model_to_dict(decoded) == encoded
    assert decoded.capabilities == model.capabilities
    assert decoded.modalities == model.modalities
    assert decoded.supports(CapabilityId("vision"))
    assert decoded.capabilities.support_of(CapabilityId("structured_output")).level is None


def test_legacy_schema_v1_without_l12_fields_is_accepted() -> None:
    encoded = model_to_dict(model_with_support())
    del encoded["capabilities"]
    del encoded["modalities"]
    result = model_from_dict(encoded)
    assert result.capabilities == CapabilitySet()
    assert result.modalities == ModalitySet()
    assert result.modalities.accepts_input(Modality("text")) is None


def test_empty_declared_output_vs_unknown_output_roundtrip() -> None:
    model = model_with_support().with_modalities(
        ModalitySet(input_modalities=None, output_modalities=frozenset())
    )
    data = model_to_dict(model)
    result = model_from_dict(data)
    assert result.modalities.accepts_input(Modality("text")) is None
    assert result.modalities.can_output(Modality("text")) is False


def test_duplicate_capabilities_in_wire_format_rejected() -> None:
    data = model_to_dict(model_with_support())
    caps = data["capabilities"]
    assert isinstance(caps, list)
    caps.append(caps[0])
    with pytest.raises(DomainValidationError, match="duplicate"):
        model_from_dict(data)


@pytest.mark.parametrize("level", ["fake", 7, True])
def test_invalid_wire_level_rejected(level: object) -> None:
    data = model_to_dict(model_with_support())
    caps = data["capabilities"]
    assert isinstance(caps, list)
    caps[0]["support"]["level"] = level
    with pytest.raises(DomainValidationError):
        model_from_dict(data)


def test_unknown_nested_capability_key_rejected() -> None:
    data = model_to_dict(model_with_support())
    caps = data["capabilities"]
    assert isinstance(caps, list)
    caps[0]["unexpected"] = "do not drop silently"
    with pytest.raises(DomainValidationError, match="unknown"):
        model_from_dict(data)


def test_unknown_nested_modality_key_rejected() -> None:
    data = model_to_dict(model_with_support())
    modes = data["modalities"]
    assert isinstance(modes, dict)
    modes["source_provider"] = "unwanted"
    with pytest.raises(DomainValidationError, match="unknown"):
        model_from_dict(data)


def test_duplicate_modality_in_wire_format_rejected() -> None:
    data = model_to_dict(model_with_support())
    modes = data["modalities"]
    assert isinstance(modes, dict)
    modes["input_modalities"] = ["text", "text"]
    with pytest.raises(DomainValidationError, match="duplicate"):
        model_from_dict(data)


def test_partial_without_explanation_rejected_by_codec() -> None:
    data = model_to_dict(model_with_support())
    caps = data["capabilities"]
    assert isinstance(caps, list)
    caps[1]["support"]["notes"] = None
    caps[1]["support"]["constraints"] = []
    with pytest.raises(DomainValidationError, match="PARTIAL"):
        model_from_dict(data)
