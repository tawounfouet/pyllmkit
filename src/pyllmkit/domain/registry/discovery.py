"""Offline catalog discovery values and provenance (ADR-046, P6 L6.6).

Discovery is descriptive, immutable and uncommitted. No clock, SDK, HTTP,
filesystem or mutable registry is accessed by this domain module.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.models import Model
from pyllmkit.domain.providers import InferenceProvider

MAX_DISCOVERY_RECORDS = 10_000
MAX_DISCOVERY_WARNINGS = 32


class MetadataSourceKind(StrEnum):
    """Only offline, explicitly supplied catalog origins are in the MVP."""

    FIXTURE = "fixture"
    STATIC_FILE = "static_file"
    EXPORT = "export"
    INTERNAL = "internal"


def _utc(value: datetime, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise DomainValidationError(f"{field_name} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class MetadataSource:
    """Stable source ID. Never store URLs, secrets or raw provider payloads."""

    kind: MetadataSourceKind
    reference: str = field(repr=False)
    authority: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, MetadataSourceKind):
            raise DomainValidationError("invalid metadata source kind")
        for name in ("reference", "authority"):
            value = getattr(self, name)
            if name == "authority" and value is None:
                continue
            if (
                type(value) is not str
                or not value.strip()
                or len(value) > 256
                or any(ord(char) < 32 for char in value)
                or any(token in value for token in ("://", "?", "=", "@"))
            ):
                raise DomainValidationError(f"{name} must be a safe opaque offline label")


@dataclass(frozen=True, slots=True)
class CatalogProvenance:
    """Provenance of one catalog record; no field-level truth assertion."""

    entity_type: str
    entity_id: str
    source: MetadataSource = field(repr=False)
    observed_at: datetime = field(repr=False)

    def __post_init__(self) -> None:
        if self.entity_type not in ("provider", "model", "deployment"):
            raise DomainValidationError("invalid provenance entity_type")
        if type(self.entity_id) is not str or not self.entity_id.strip():
            raise DomainValidationError("invalid provenance entity_id")
        if not isinstance(self.source, MetadataSource):
            raise DomainValidationError("source must be MetadataSource")
        _utc(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Candidate tuples from an offline source. Duplicate IDs are rejected."""

    source: MetadataSource
    observed_at: datetime = field(repr=False)
    providers: tuple[InferenceProvider, ...] = field(default=(), repr=False)
    models: tuple[Model, ...] = field(default=(), repr=False)
    deployments: tuple[Deployment, ...] = field(default=(), repr=False)
    warnings: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, MetadataSource):
            raise DomainValidationError("source must be MetadataSource")
        _utc(self.observed_at, "observed_at")
        for name, expected_type in (
            ("providers", InferenceProvider),
            ("models", Model),
            ("deployments", Deployment),
        ):
            data = getattr(self, name)
            if (
                not isinstance(data, tuple)
                or len(data) > MAX_DISCOVERY_RECORDS
                or any(not isinstance(item, expected_type) for item in data)
            ):
                raise DomainValidationError(f"{name} must be bounded typed tuple")
            keys = [item.id.value for item in data]
            if len(set(keys)) != len(keys):
                raise DomainValidationError(f"{name} contains duplicate canonical IDs")
        if (
            not isinstance(self.warnings, tuple)
            or len(self.warnings) > MAX_DISCOVERY_WARNINGS
            or any(type(item) is not str or not item.strip() or len(item) > 200
                   for item in self.warnings)
        ):
            raise DomainValidationError("warnings must be bounded nonblank strings")


def validate_discovery_time(
    result: DiscoveryResult,
    *,
    now: datetime,
    max_future_skew: timedelta = timedelta(0),
) -> None:
    """Validate freshness against an explicit injected UTC clock; never sample time."""
    if not isinstance(result, DiscoveryResult):
        raise DomainValidationError("expected DiscoveryResult")
    _utc(now, "now")
    if not isinstance(max_future_skew, timedelta) or max_future_skew < timedelta(0):
        raise DomainValidationError("max_future_skew must be nonnegative timedelta")
    if result.observed_at > now + max_future_skew:
        raise DomainValidationError("discovery observation exceeds allowed future skew")
