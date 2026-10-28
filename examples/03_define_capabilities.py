"""L1.2: pure description of a multimodal LLM, with no provider calls."""

from pyllmkit.domain.capabilities import (
    Capability, CapabilityId, CapabilitySet, CapabilitySupport, SupportLevel,
)
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import (
    Model, ModelFamily, ModelId, ModelIdentity, model_to_dict,
)

model = Model(
    id=ModelId("example/multimodal"),
    identity=ModelIdentity(family=ModelFamily("example")),
    capabilities=CapabilitySet((
        Capability(CapabilityId("vision"), CapabilitySupport(SupportLevel.NATIVE)),
        Capability(CapabilityId("tool_calling"), CapabilitySupport(SupportLevel.EMULATED)),
    )),
    modalities=ModalitySet(
        input_modalities=frozenset({Modality("text"), Modality("image")}),
        output_modalities=frozenset({Modality("text")}),
    ),
)
assert model.supports(CapabilityId("vision"))
assert model.modalities.can_output(Modality("image")) is False
print(model_to_dict(model))
