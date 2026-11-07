"""Versioned, credential-free model-listing snapshots for M1.

A provider /models listing is an observation, NOT verified media generation,
account permission, a model capability guarantee or a full inventory.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyllmkit.adapters.cli.media_catalog_v2 import _identifier

SCHEMA_VERSION = 2
MAX_CACHE_BYTES = 1_048_576
ENDPOINTS = {
    "openai": "https://api.openai.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "google": "https://generativelanguage.googleapis.com/v1beta/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "xai": "https://api.x.ai/v1/models",
    "ollama": "http://127.0.0.1:11434/api/tags",
}


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    provider: str
    model_ids: tuple[str, ...]
    observed_at: datetime
    endpoint: str
    complete: bool = False


@dataclass(frozen=True, slots=True)
class DiscoverySnapshot:
    schema_version: int
    revision: int
    observations: tuple[ProviderObservation, ...]

    def observed_ids(self) -> dict[str, set[str]]:
        return {item.provider: set(item.model_ids) for item in self.observations}


def _parse_observation(raw: object) -> ProviderObservation:
    if type(raw) is not dict:
        raise ValueError("invalid_discovery_observation")
    provider = raw.get("provider")
    if type(provider) is not str or provider not in ENDPOINTS:
        raise ValueError("unknown_discovery_provider")
    endpoint = raw.get("endpoint")
    if endpoint != ENDPOINTS[provider]:
        raise ValueError("invalid_discovery_endpoint")
    ids = raw.get("model_ids")
    if type(ids) is not list or len(ids) > 3000:
        raise ValueError("invalid_discovery_models")
    models = tuple(_identifier(value, "discovery_model") for value in ids)
    if len(set(models)) != len(models):
        raise ValueError("duplicate_discovery_model")
    complete = raw.get("complete", False)
    if complete is not False:
        # An incomplete, non-paginated list MUST NOT become source of retirement.
        raise ValueError("unverified_discovery_completeness")
    stamp = raw.get("observed_at")
    if type(stamp) is not str:
        raise ValueError("invalid_discovery_timestamp")
    try:
        instant = datetime.fromisoformat(stamp)
    except ValueError:
        raise ValueError("invalid_discovery_timestamp") from None
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("naive_discovery_timestamp")
    return ProviderObservation(provider, models, instant, endpoint)


def parse_discovery_snapshot(data: object) -> DiscoverySnapshot:
    if type(data) is not dict or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported_discovery_snapshot_schema")
    revision = data.get("revision")
    if type(revision) is not int or revision < 1:
        raise ValueError("invalid_discovery_revision")
    entries = data.get("observations")
    if type(entries) is not list or len(entries) > len(ENDPOINTS):
        raise ValueError("invalid_discovery_observations")
    observations = tuple(_parse_observation(item) for item in entries)
    if len({item.provider for item in observations}) != len(observations):
        raise ValueError("duplicate_discovery_provider")
    return DiscoverySnapshot(SCHEMA_VERSION, revision, observations)


def snapshot_path(legacy_path: Path) -> Path:
    """Co-locate cache v2 without breaking legacy discovered_models.json readers."""
    return legacy_path.with_name("discovered_models_v2.json")


def load_discovery_snapshot(path: Path) -> DiscoverySnapshot:
    if not path.exists():
        return DiscoverySnapshot(SCHEMA_VERSION, 1, ())
    if path.stat().st_size > MAX_CACHE_BYTES:
        raise ValueError("discovery_snapshot_too_large")
    with path.open(encoding="utf-8") as stream:
        return parse_discovery_snapshot(json.load(stream))


def update_discovery_snapshot(
    path: Path,
    successful: dict[str, list[str]],
    *,
    observed_at: datetime | None = None,
) -> DiscoverySnapshot:
    """Replace only providers with a successful listing. Keep others unchanged.

    Writes an atomic 0600 local cache containing IDs and endpoint only.
    Never persists API keys, response headers, or arbitrary provider metadata.
    """
    previous = load_discovery_snapshot(path)
    instant = observed_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("naive_discovery_timestamp")
    merged = {item.provider: item for item in previous.observations}
    for provider, model_ids in successful.items():
        if provider not in ENDPOINTS:
            raise ValueError("unknown_discovery_provider")
        models = sorted(set(model_ids))
        row = {
            "provider": provider,
            "endpoint": ENDPOINTS[provider],
            "observed_at": instant.isoformat(),
            "model_ids": models,
            "complete": False,
        }
        merged[provider] = _parse_observation(row)
    snapshot = DiscoverySnapshot(
        SCHEMA_VERSION, previous.revision + 1,
        tuple(merged[key] for key in sorted(merged)),
    )
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "revision": snapshot.revision,
        "observations": [
            {
                "provider": item.provider,
                "endpoint": item.endpoint,
                "model_ids": list(item.model_ids),
                "observed_at": item.observed_at.isoformat(),
                "complete": False,
            }
            for item in snapshot.observations
        ],
    }
    payload = json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if len(payload) > MAX_CACHE_BYTES:
        raise ValueError("discovery_snapshot_too_large")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".discovery-v2-", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            os.chmod(temp_path, 0o600)
            stream.write(payload)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return snapshot
