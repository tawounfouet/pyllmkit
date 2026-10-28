"""Source-derived Phase 1 AC acceptance evidence.

AC-001, AC-002, AC-004, AC-005 and AC-018 apply to M1.
This file deliberately does NOT claim any inference/deployment/registry AC.
"""

import os
import socket

import pytest

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import (
    Model,
    ModelFamily,
    ModelId,
    ModelIdentity,
    ModelVariant,
    ModelVersion,
    model_from_dict,
    model_to_dict,
)


def test_ac_001_model_instantiation_requires_no_provider_sdk() -> None:
    model = Model(ModelId("example/alpha"), ModelIdentity(family=ModelFamily("example")))
    assert model.id == ModelId("example/alpha")
    assert model.architecture is None


def test_ac_002_family_can_have_multiple_versions_and_variants() -> None:
    family = ModelFamily("example")
    first = Model(
        ModelId("example/1/base"),
        ModelIdentity(family, ModelVersion("v1"), ModelVariant("base")),
    )
    second = Model(
        ModelId("example/2/large"),
        ModelIdentity(family, ModelVersion("2026-10"), ModelVariant("large")),
    )
    assert first.identity.family == second.identity.family
    assert first.identity.version != second.identity.version
    assert first.identity.variant != second.identity.variant
    assert first != second


def test_ac_004_directional_modalities_and_unknown() -> None:
    model = Model(
        ModelId("example/multimodal"),
        ModelIdentity(ModelFamily("example")),
        modalities=ModalitySet(
            input_modalities=frozenset({Modality("image"), Modality("text")}),
            output_modalities=frozenset({Modality("text")}),
        ),
    )
    assert model.modalities.accepts_input(Modality("image")) is True
    assert model.modalities.can_output(Modality("image")) is False
    assert Model(ModelId("unknown"), ModelIdentity(ModelFamily("example"))).modalities.can_output(
        Modality("text")
    ) is None


def test_ac_005_support_and_unknown_are_distinct() -> None:
    vision = CapabilityId("vision")
    model = Model(
        ModelId("example/vision"),
        ModelIdentity(ModelFamily("example")),
        capabilities=CapabilitySet(
            (Capability(vision, CapabilitySupport(SupportLevel.NATIVE)),)
        ),
    )
    assert model.supports(vision) is True
    assert model.capabilities.support_of(CapabilityId("tool_calling")).level is None
    assert model_from_dict(model_to_dict(model)).capabilities == model.capabilities


def test_ac_018_network_and_keys_are_unavailable_in_domain_tests() -> None:
    assert os.environ.get("OPENAI_API_KEY") is None
    assert os.environ.get("ANTHROPIC_API_KEY") is None
    with pytest.raises(RuntimeError, match="Network access is forbidden"):
        socket.create_connection(("127.0.0.1", 1), timeout=0.01)
    with pytest.raises(RuntimeError, match="Network access is forbidden"):
        socket.socket().connect(("127.0.0.1", 1))
