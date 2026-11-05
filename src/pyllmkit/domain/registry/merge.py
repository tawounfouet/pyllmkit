"""Immutable preview, conflict and snapshot contracts for offline catalog merging."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.models import Model
from pyllmkit.domain.providers import InferenceProvider

from .discovery import CatalogProvenance, MetadataSource


class MergePolicy(StrEnum):
    """Fail closed. Higher-precedence override requires a future dedicated ADR."""

    FAIL_ON_CONFLICT = "fail_on_conflict"


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    """Atomic immutable catalog projection with a monotonic revision."""

    revision: int
    models: tuple[Model, ...] = field(repr=False)
    providers: tuple[InferenceProvider, ...] = field(repr=False)
    deployments: tuple[Deployment, ...] = field(repr=False)
    provenance: tuple[CatalogProvenance, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.revision) is not int or self.revision < 0:
            raise DomainValidationError("revision must be nonnegative int")
        for name, expected_type in (
            ("models", Model),
            ("providers", InferenceProvider),
            ("deployments", Deployment),
            ("provenance", CatalogProvenance),
        ):
            records = getattr(self, name)
            if not isinstance(records, tuple) or any(
                not isinstance(record, expected_type) for record in records
            ):
                raise DomainValidationError(f"{name} must be typed tuple")
            keys = [
                (record.entity_type, record.entity_id)
                if name == "provenance" else record.id.value
                for record in records
            ]
            if len(set(keys)) != len(keys):
                raise DomainValidationError(f"{name} contains duplicate canonical IDs")


@dataclass(frozen=True, slots=True)
class CatalogChange:
    """One proposed addition or an identical replay, with incoming provenance."""

    entity_type: str
    entity_id: str
    provenance: CatalogProvenance = field(repr=False)


@dataclass(frozen=True, slots=True)
class RegistryConflict:
    """Field-level metadata disagreement, without recording sensitive values."""

    entity_type: str
    entity_id: str
    changed_fields: tuple[str, ...]
    incoming_provenance: CatalogProvenance = field(repr=False)
    existing_provenance: CatalogProvenance | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class InvalidCatalogReference:
    """Incoming deployment references an absent canonical model/provider."""

    deployment_id: str
    missing_type: str
    missing_id: str


@dataclass(frozen=True, slots=True)
class MergePreview:
    """Dry-run output; no mutation, no ranking, and no implicit import."""

    revision: int
    policy: MergePolicy
    source: MetadataSource = field(repr=False)
    observed_at: datetime = field(repr=False)
    candidate_digest: str = field(repr=False)
    additions: tuple[CatalogChange, ...] = ()
    unchanged: tuple[CatalogChange, ...] = ()
    conflicts: tuple[RegistryConflict, ...] = ()
    invalid_references: tuple[InvalidCatalogReference, ...] = ()

    @property
    def can_apply(self) -> bool:
        return not (self.conflicts or self.invalid_references)

    @property
    def no_op(self) -> bool:
        return self.can_apply and not self.additions


@dataclass(frozen=True, slots=True)
class MergeResult:
    """Commit result or idempotent no-op; never a claim of provider health."""

    preview: MergePreview
    applied: bool
    revision: int
