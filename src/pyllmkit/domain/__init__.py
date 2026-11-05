"""Public provider-agnostic Domain API (M1 and Phase 2 interactions).

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
from .interactions import (
    Content,
    ContentPart,
    INTERACTION_SCHEMA_VERSION,
    ImageContent,
    MediaSourceRef,
    Message,
    Role,
    TextContent,
    message_from_dict,
    message_to_dict,
)
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
    "Content",
    "ContentPart",
    "DomainValidationError",
    "ImageContent",
    "INTERACTION_SCHEMA_VERSION",
    "MediaSourceRef",
    "Message",
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
    "Role",
    "SupportLevel",
    "TextContent",
    "artifact_from_dict",
    "artifact_to_dict",
    "model_from_dict",
    "model_to_dict",
    "message_from_dict",
    "message_to_dict",
]
