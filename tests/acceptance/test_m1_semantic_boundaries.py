"""Acceptance evidence for explicit Phase 1 domain boundaries.

These tests target TEST-MOD02 (IMAGE != VISION) and MODEL-016/017
(provider-scoped external aliases), not provider inference support.
"""

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
    ProviderModelRef,
)


def test_mod02_image_modality_is_not_vision_capability() -> None:
    """Accepting image input never asserts vision capability implicitly."""
    image_input = Model(
        id=ModelId("example/image-input"),
        identity=ModelIdentity(family=ModelFamily("example")),
        modalities=ModalitySet(
            input_modalities=frozenset({Modality("text"), Modality("image")}),
            output_modalities=frozenset({Modality("text")}),
        ),
    )
    assert image_input.modalities.accepts_input(Modality("image")) is True
    assert image_input.capabilities.support_of(CapabilityId("vision")).level is None
    assert image_input.supports(CapabilityId("vision")) is False

    vision_declared = Model(
        id=ModelId("example/vision-declared"),
        identity=ModelIdentity(family=ModelFamily("example")),
        capabilities=CapabilitySet(
            (Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),)
        ),
    )
    assert vision_declared.supports(CapabilityId("vision")) is True
    assert vision_declared.modalities.accepts_input(Modality("image")) is None


def test_model_016_017_alias_is_scoped_by_provider() -> None:
    """Two providers can expose the same alias without defining model identity."""
    model_id = ModelId("canonical/model")
    first = ProviderModelRef("provider_a", model_id, "same-external-name")
    second = ProviderModelRef("provider_b", model_id, "same-external-name")
    model = Model(
        id=model_id,
        identity=ModelIdentity(family=ModelFamily("canonical")),
        provider_refs=(first, second),
    )
    assert first != second
    assert first.provider_model_name == second.provider_model_name
    assert first.provider_id != second.provider_id
    assert model.id == first.model_id == second.model_id
