"""Explicit versioned Model Domain codec; no wire format is provider-owned.

Unknown *values* are preserved as None. Unknown *schema keys* are rejected,
rather than silently dropped, pending a forward-compatible extensions ADR.
"""

from collections.abc import Mapping
from typing import cast

from pyllmkit.domain.errors import DomainValidationError

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
from .schema_l12 import (
    capabilities_from_object,
    capabilities_to_object,
    modalities_from_object,
    modalities_to_object,
)


SCHEMA_VERSION = 1


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise DomainValidationError(f"{label} must be an object with string keys")
    return cast(Mapping[str, object], value)


def _allowed(data: Mapping[str, object], fields: set[str], label: str) -> None:
    extras = set(data) - fields
    if extras:
        raise DomainValidationError(f"unknown {label} keys: {sorted(extras)}")


def _string(data: Mapping[str, object], key: str, *, required: bool = False) -> str | None:
    value = data.get(key)
    if value is None:
        if required:
            raise DomainValidationError(f"{key} is required")
        return None
    if not isinstance(value, str):
        raise DomainValidationError(f"{key} must be string or null")
    return value


def _integer(data: Mapping[str, object], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if type(value) is not int:
        raise DomainValidationError(f"{key} must be integer or null")
    return value


def _boolean(data: Mapping[str, object], key: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise DomainValidationError(f"{key} must be boolean or null")
    return value


def _require_string(data: Mapping[str, object], key: str) -> str:
    value = _string(data, key, required=True)
    assert value is not None
    return value


def _check_schema(data: Mapping[str, object]) -> None:
    version = data.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise DomainValidationError(f"unsupported or absent schema_version: {version!r}")


def model_to_dict(model: Model) -> dict[str, object]:
    """Serialize a Model snapshot with explicit schema and nullable values."""
    identity = {
        "family": model.identity.family.value,
        "version": model.identity.version.value if model.identity.version else None,
        "variant": model.identity.variant.value if model.identity.variant else None,
        "revision": model.identity.revision.value if model.identity.revision else None,
        "developer": model.identity.developer,
        "specialization": model.identity.specialization,
    }
    architecture: dict[str, object] | None = None
    if model.architecture is not None:
        architecture = {
            "architecture_type": model.architecture.architecture_type,
            "parameter_count": model.architecture.parameter_count,
            "layer_count": model.architecture.layer_count,
            "hidden_size": model.architecture.hidden_size,
            "attention_type": model.architecture.attention_type,
            "mixture_of_experts": model.architecture.mixture_of_experts,
        }
    limits: dict[str, object] | None = None
    if model.limits is not None:
        limits = {
            "context_window": model.limits.context_window,
            "max_input_tokens": model.limits.max_input_tokens,
            "max_output_tokens": model.limits.max_output_tokens,
            "max_images": model.limits.max_images,
            "max_tool_calls": model.limits.max_tool_calls,
            "max_tools": model.limits.max_tools,
        }
    provider_refs: list[dict[str, object]] = [
        {
            "provider_id": ref.provider_id,
            "model_id": ref.model_id.value,
            "provider_model_name": ref.provider_model_name,
            "api_version": ref.api_version,
        }
        for ref in model.provider_refs
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "id": model.id.value,
        "identity": identity,
        "architecture": architecture,
        "limits": limits,
        "provider_refs": provider_refs,
        "capabilities": capabilities_to_object(model.capabilities),
        "modalities": modalities_to_object(model.modalities),
    }


def model_from_dict(payload: Mapping[str, object]) -> Model:
    """Decode a Model; reject schema changes rather than losing unknown data."""
    _allowed(
        payload,
        {"schema_version", "id", "identity", "architecture", "limits", "provider_refs",
         "capabilities", "modalities"},
        "model",
    )
    _check_schema(payload)
    model_id = ModelId(_require_string(payload, "id"))
    i = _mapping(payload.get("identity"), "identity")
    _allowed(
        i, {"family", "version", "variant", "revision", "developer", "specialization"},
        "identity",
    )
    version = _string(i, "version")
    variant = _string(i, "variant")
    revision = _string(i, "revision")
    identity = ModelIdentity(
        family=ModelFamily(_require_string(i, "family")),
        version=ModelVersion(version) if version is not None else None,
        variant=ModelVariant(variant) if variant is not None else None,
        revision=ModelRevision(revision) if revision is not None else None,
        developer=_string(i, "developer"),
        specialization=_string(i, "specialization"),
    )
    architecture = None
    if payload.get("architecture") is not None:
        a = _mapping(payload["architecture"], "architecture")
        _allowed(
            a,
            {
                "architecture_type", "parameter_count", "layer_count", "hidden_size",
                "attention_type", "mixture_of_experts",
            },
            "architecture",
        )
        architecture = ModelArchitecture(
            architecture_type=_string(a, "architecture_type"),
            parameter_count=_integer(a, "parameter_count"),
            layer_count=_integer(a, "layer_count"),
            hidden_size=_integer(a, "hidden_size"),
            attention_type=_string(a, "attention_type"),
            mixture_of_experts=_boolean(a, "mixture_of_experts"),
        )
    limits = None
    if payload.get("limits") is not None:
        limits_data = _mapping(payload["limits"], "limits")
        _allowed(
            limits_data,
            {
                "context_window", "max_input_tokens", "max_output_tokens",
                "max_images", "max_tool_calls", "max_tools",
            },
            "limits",
        )
        limits = ModelLimits(
            context_window=_integer(limits_data, "context_window"),
            max_input_tokens=_integer(limits_data, "max_input_tokens"),
            max_output_tokens=_integer(limits_data, "max_output_tokens"),
            max_images=_integer(limits_data, "max_images"),
            max_tool_calls=_integer(limits_data, "max_tool_calls"),
            max_tools=_integer(limits_data, "max_tools"),
        )
    raw_refs = payload.get("provider_refs", [])
    if not isinstance(raw_refs, list):
        raise DomainValidationError("provider_refs must be a list")
    refs: list[ProviderModelRef] = []
    for raw in raw_refs:
        ref = _mapping(raw, "provider ref")
        _allowed(
            ref, {"provider_id", "model_id", "provider_model_name", "api_version"},
            "provider ref",
        )
        refs.append(
            ProviderModelRef(
                provider_id=_require_string(ref, "provider_id"),
                model_id=ModelId(_require_string(ref, "model_id")),
                provider_model_name=_require_string(ref, "provider_model_name"),
                api_version=_string(ref, "api_version"),
            )
        )
    return Model(
        id=model_id,
        identity=identity,
        architecture=architecture,
        limits=limits,
        provider_refs=tuple(refs),
        capabilities=capabilities_from_object(payload.get("capabilities", [])),
        modalities=modalities_from_object(payload.get("modalities", None)),
    )


def artifact_to_dict(artifact: ModelArtifact) -> dict[str, object]:
    """Serialize one Artifact (not an embedded Deployment)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "id": artifact.id.value,
        "model_id": artifact.model_id.value,
        "format": artifact.format,
        "precision": artifact.precision,
        "quantization": artifact.quantization,
        "size_bytes": artifact.size_bytes,
        "source": artifact.source,
        "checksum": artifact.checksum,
        "revision": artifact.revision.value if artifact.revision is not None else None,
    }


def artifact_from_dict(payload: Mapping[str, object]) -> ModelArtifact:
    """Decode an independently identified ModelArtifact."""
    _allowed(
        payload,
        {
            "schema_version", "id", "model_id", "format", "precision", "quantization",
            "size_bytes", "source", "checksum", "revision",
        },
        "artifact",
    )
    _check_schema(payload)
    revision = _string(payload, "revision")
    return ModelArtifact(
        id=ModelArtifactId(_require_string(payload, "id")),
        model_id=ModelId(_require_string(payload, "model_id")),
        format=_require_string(payload, "format"),
        precision=_string(payload, "precision"),
        quantization=_string(payload, "quantization"),
        size_bytes=_integer(payload, "size_bytes"),
        source=_string(payload, "source"),
        checksum=_string(payload, "checksum"),
        revision=ModelRevision(revision) if revision is not None else None,
    )
