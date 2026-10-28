"""Public Phase 1 Domain API.

Subpackages remain valid canonical import paths; explicit root reexports
are ergonomic alpha aliases, not a provider-specific SDK facade.
"""

from .capabilities import (
    Capability,
    CapabilityConstraint,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from .errors import DomainValidationError, PyLLMKitError
from .modalities import Modality, ModalitySet
from .models import (
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

__all__ = [
    "Capability",
    "CapabilityConstraint",
    "CapabilityId",
    "CapabilitySet",
    "CapabilitySupport",
    "DomainValidationError",
    "Model",
    "ModelArchitecture",
    "ModelArtifact",
    "ModelArtifactId",
    "ModelFamily",
    "ModelId",
    "ModelIdentity",
    "ModelLimits",
    "ModelRevision",
    "ModelVariant",
    "ModelVersion",
    "Modality",
    "ModalitySet",
    "ProviderModelRef",
    "PyLLMKitError",
    "SupportLevel",
    "artifact_from_dict",
    "artifact_to_dict",
    "model_from_dict",
    "model_to_dict",
]
