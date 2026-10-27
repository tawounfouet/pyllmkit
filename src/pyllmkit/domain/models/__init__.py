"""Canonical public entrypoint for Model Domain (Phase 1, L1.1)."""

from .artifact import ModelArtifact
from .descriptors import (
    ModelArchitecture,
    ModelFamily,
    ModelLimits,
    ModelRevision,
    ModelVariant,
    ModelVersion,
)
from .identifiers import ModelArtifactId, ModelId
from .identity import ModelIdentity
from .model import Model, ProviderModelRef
from .serialization import (
    SCHEMA_VERSION,
    artifact_from_dict,
    artifact_to_dict,
    model_from_dict,
    model_to_dict,
)

__all__ = [
    "Model",
    "ModelId",
    "ModelIdentity",
    "ModelFamily",
    "ModelVersion",
    "ModelVariant",
    "ModelRevision",
    "ModelArchitecture",
    "ModelLimits",
    "ModelArtifact",
    "ModelArtifactId",
    "ProviderModelRef",
    "SCHEMA_VERSION",
    "model_to_dict",
    "model_from_dict",
    "artifact_to_dict",
    "artifact_from_dict",
]
