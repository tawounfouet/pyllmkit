"""Versioned multimodal catalogue and deterministic offline reconciliation (M1).

Infrastructure/read-model adapter: existing domain Model, Deployment and provider
identity remain authoritative for inference. A catalogue entry is never evidence
of account access, a billable price or successful media generation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from pyllmkit.adapters.inference.media_lifecycle import MediaLifecycle, media_model_policy

SCHEMA_VERSION = 2
CATALOG_PATH = Path(__file__).parent / "data" / "media_catalog_v2.json"
MEDIA_TASKS = frozenset({
    "text_to_image", "image_edit", "text_to_video", "image_to_video",
    "text_to_speech", "speech_to_speech", "text_to_music", "text_to_sfx",
})
_MODALITIES = frozenset({"text", "image", "audio", "video"})
_ALLOWED_AVAILABILITY = frozenset({"catalog_only", "observed", "account_restricted", "unknown"})
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")


@dataclass(frozen=True, slots=True)
class CapabilityMatrix:
    """Explicit media-task claims. Empty tuples and None mean *unknown*."""

    tasks: tuple[str, ...]
    modalities_in: tuple[str, ...]
    modalities_out: tuple[str, ...]
    resolutions: tuple[str, ...] = ()
    duration_seconds: tuple[int, ...] = ()
    codecs: tuple[str, ...] = ()
    aspect_ratios: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    voices: tuple[str, ...] = ()
    max_outputs: int | None = None
    reference_image: bool | None = None
    api_sync: bool | None = None
    api_async: bool | None = None


@dataclass(frozen=True, slots=True)
class MediaModelDescriptor:
    """Read-only route, lifecycle and provenance of a declared media model."""

    public_model_id: str
    native_model_id: str
    model_owner: str
    api_provider: str
    billing_provider: str
    deployment_channel: str
    lifecycle: MediaLifecycle
    availability: str
    capabilities: CapabilityMatrix
    aliases: tuple[str, ...]
    source_url: str
    verified_at: date | None


@dataclass(frozen=True, slots=True)
class MediaCatalog:
    schema_version: int
    revision: str
    updated_at: date
    models: tuple[MediaModelDescriptor, ...]

    def find(self, identifier: str, *, provider: str | None = None) -> MediaModelDescriptor | None:
        """Exact-ID/alias resolution; never select an ambiguous provider or fallback."""
        if not identifier or not identifier.strip():
            return None
        identity = identifier.strip().lower()
        matches = [
            model for model in self.models
            if (provider is None or model.api_provider == provider.lower().strip())
            and (
                model.public_model_id.lower() == identity
                or identity in (alias.lower() for alias in model.aliases)
            )
        ]
        if len(matches) > 1:
            raise ValueError("ambiguous_model_identifier")
        return matches[0] if matches else None

    def list(
        self, *, provider: str | None = None, task: str | None = None,
    ) -> tuple[MediaModelDescriptor, ...]:
        if task is not None and task not in MEDIA_TASKS:
            raise ValueError("unsupported_media_task")
        return tuple(
            m for m in self.models
            if (provider is None or m.api_provider == provider.lower().strip())
            and (task is None or task in m.capabilities.tasks)
        )


def _identifier(value: object, field_name: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid_{field_name}")
    return value


def _strings(raw: object, allowed: frozenset[str] | None = None) -> tuple[str, ...]:
    if type(raw) is not list:
        raise ValueError("invalid_capability_list")
    result: list[str] = []
    for value in raw:
        if type(value) is not str or not value.strip() or len(value) > 128:
            raise ValueError("invalid_capability_value")
        if allowed is not None and value not in allowed:
            raise ValueError("unsupported_capability_value")
        if value in result:
            raise ValueError("duplicate_capability_value")
        result.append(value)
    return tuple(result)


def _optional_bool(value: object) -> bool | None:
    if value is None or type(value) is bool:
        return value
    raise ValueError("invalid_capability_boolean")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 1:
        raise ValueError("invalid_capability_number")
    return value


def _matrix(raw: object) -> CapabilityMatrix:
    if type(raw) is not dict:
        raise ValueError("invalid_capability_matrix")
    tasks = _strings(raw.get("tasks", []), MEDIA_TASKS)
    incoming = _strings(raw.get("modalities_in", []), _MODALITIES)
    outgoing = _strings(raw.get("modalities_out", []), _MODALITIES)
    if not tasks or not incoming or not outgoing:
        raise ValueError("missing_media_capabilities")
    durations_raw = raw.get("duration_seconds", [])
    if type(durations_raw) is not list or any(type(v) is not int or v <= 0 for v in durations_raw):
        raise ValueError("invalid_media_durations")
    if len(set(durations_raw)) != len(durations_raw):
        raise ValueError("duplicate_media_duration")
    return CapabilityMatrix(
        tasks, incoming, outgoing,
        resolutions=_strings(raw.get("resolutions", [])),
        duration_seconds=tuple(durations_raw),
        codecs=_strings(raw.get("codecs", [])),
        aspect_ratios=_strings(raw.get("aspect_ratios", [])),
        languages=_strings(raw.get("languages", [])),
        voices=_strings(raw.get("voices", [])),
        max_outputs=_optional_int(raw.get("max_outputs")),
        reference_image=_optional_bool(raw.get("reference_image")),
        api_sync=_optional_bool(raw.get("api_sync")),
        api_async=_optional_bool(raw.get("api_async")),
    )


def _descriptor(raw: object) -> MediaModelDescriptor:
    if type(raw) is not dict:
        raise ValueError("invalid_media_descriptor")
    model_id = _identifier(raw.get("public_model_id"), "public_model_id")
    provider = _identifier(raw.get("api_provider"), "api_provider").lower()
    owner = _identifier(raw.get("model_owner"), "model_owner").lower()
    billing = _identifier(raw.get("billing_provider"), "billing_provider").lower()
    channel = _identifier(raw.get("deployment_channel"), "deployment_channel")
    native = _identifier(raw.get("native_model_id"), "native_model_id")
    if type(raw.get("lifecycle")) is not str:
        raise ValueError("invalid_media_lifecycle")
    try:
        state = MediaLifecycle(raw["lifecycle"])
    except ValueError:
        raise ValueError("invalid_media_lifecycle") from None
    availability = raw.get("availability")
    if availability not in _ALLOWED_AVAILABILITY:
        raise ValueError("invalid_model_availability")
    source_url = raw.get("source_url")
    if type(source_url) is not str or not source_url.startswith("https://") or len(source_url) > 2048:
        raise ValueError("invalid_media_provenance")
    raw_date = raw.get("verified_at")
    if raw_date is not None and type(raw_date) is not str:
        raise ValueError("invalid_media_verification_date")
    try:
        verified_at = date.fromisoformat(raw_date) if raw_date else None
    except ValueError:
        raise ValueError("invalid_media_verification_date") from None
    aliases = _strings(raw.get("aliases", []))
    if any(not _IDENTIFIER.fullmatch(a) for a in aliases):
        raise ValueError("invalid_model_alias")
    if model_id in aliases or native in aliases:
        raise ValueError("self_referencing_model_alias")
    return MediaModelDescriptor(
        public_model_id=model_id,
        native_model_id=native,
        model_owner=owner,
        api_provider=provider,
        billing_provider=billing,
        deployment_channel=channel,
        lifecycle=state,
        availability=availability,
        capabilities=_matrix(raw.get("capabilities")),
        aliases=aliases,
        source_url=source_url,
        verified_at=verified_at,
    )


def parse_media_catalog(payload: object) -> MediaCatalog:
    """Strict schema v2 loader; no silent acceptance of v1 or malformed overrides."""
    if type(payload) is not dict or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported_media_catalog_schema")
    revision = payload.get("revision")
    if type(revision) is not str or not revision.strip() or len(revision) > 100:
        raise ValueError("invalid_catalog_revision")
    stamp = payload.get("updated_at")
    if type(stamp) is not str:
        raise ValueError("invalid_catalog_date")
    try:
        updated_at = date.fromisoformat(stamp)
    except ValueError:
        raise ValueError("invalid_catalog_date") from None
    values = payload.get("models")
    if type(values) is not list or len(values) > 2000:
        raise ValueError("invalid_catalog_entries")
    models = tuple(_descriptor(item) for item in values)
    seen: set[tuple[str, str]] = set()
    public_ids: dict[str, set[str]] = {}
    for model in models:
        scope = (model.api_provider, model.public_model_id.lower())
        if scope in seen:
            raise ValueError("duplicate_provider_model")
        seen.add(scope)
        known = public_ids.setdefault(model.api_provider, set())
        for identifier in (model.public_model_id, *model.aliases):
            token = identifier.lower()
            if token in known:
                raise ValueError("ambiguous_provider_alias")
            known.add(token)
    return MediaCatalog(SCHEMA_VERSION, revision, updated_at, models)


def load_media_catalog(path: Path | None = None) -> MediaCatalog:
    """Load bounded, versioned JSON (never fetch the network)."""
    target = path if path is not None else CATALOG_PATH
    if target.stat().st_size > 2_000_000:
        raise ValueError("media_catalog_too_large")
    with target.open(encoding="utf-8") as stream:
        return parse_media_catalog(json.load(stream))


def effective_lifecycle(model: MediaModelDescriptor, *, on_date: date | None = None) -> MediaLifecycle:
    """M0 retirement notices take precedence over static and discovered metadata."""
    inherited = media_model_policy(model.public_model_id, on_date=on_date)
    if inherited.state is MediaLifecycle.RETIRED:
        return MediaLifecycle.RETIRED
    if inherited.state is MediaLifecycle.UNVERIFIED:
        return MediaLifecycle.UNVERIFIED
    if model.lifecycle is MediaLifecycle.RETIRED:
        return MediaLifecycle.RETIRED
    return inherited.state if inherited.state is not MediaLifecycle.UNKNOWN else model.lifecycle


def reconcile_observed_ids(
    catalog: MediaCatalog, observed: dict[str, set[str]],
) -> tuple[dict[str, str], ...]:
    """Compare catalogue vs provider model listings without claiming callable access.

    Missing IDs are *not* retired: API listings can be partial, paginated or scoped.
    """
    result: list[dict[str, str]] = []
    found: set[tuple[str, str]] = set()
    for model in sorted(catalog.models, key=lambda m: (m.api_provider, m.public_model_id)):
        provider = model.api_provider
        identity = model.public_model_id
        listed = identity in observed.get(provider, set())
        if listed:
            found.add((provider, identity))
        lifecycle = effective_lifecycle(model)
        result.append({
            "provider": provider,
            "model": identity,
            "comparison": "observed" if listed else "catalog_only",
            "lifecycle": lifecycle.value,
        })
    for provider, models in sorted(observed.items()):
        for identity in sorted(models):
            if (provider, identity) not in found and catalog.find(identity, provider=provider) is None:
                result.append({
                    "provider": provider, "model": identity,
                    "comparison": "observed_only", "lifecycle": MediaLifecycle.UNKNOWN.value,
                })
    return tuple(result)


def diff_media_catalog(left: MediaCatalog, right: MediaCatalog) -> dict[str, tuple[str, ...]]:
    """Deterministic offline diff of two versioned snapshots, provider-qualified."""
    old = {(m.api_provider, m.public_model_id): m for m in left.models}
    new = {(m.api_provider, m.public_model_id): m for m in right.models}
    fmt = lambda key: f"{key[0]}:{key[1]}"
    return {
        "added": tuple(sorted(fmt(key) for key in new.keys() - old.keys())),
        "removed": tuple(sorted(fmt(key) for key in old.keys() - new.keys())),
        "changed": tuple(sorted(fmt(key) for key in old.keys() & new.keys() if old[key] != new[key])),
    }
