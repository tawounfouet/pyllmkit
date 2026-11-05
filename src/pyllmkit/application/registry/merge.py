"""Offline discovery preview and opt-in, atomic three-registry merge (ADR-047).

All decisions are calculated from a versioned catalog snapshot. No change is
applied before the entire batch passes conflict and referential validation.
"""

import json
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
from typing import TypeVar

from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.models import Model
from pyllmkit.domain.providers import InferenceProvider
from pyllmkit.domain.registry import (
    CatalogChange,
    CatalogProvenance,
    DiscoveryResult,
    InvalidCatalogReference,
    MergePolicy,
    MergePreview,
    MergeResult,
    RegistryConflict,
    RegistryMergeRejectedError,
    RegistrySnapshot,
    RegistryStaleSnapshotError,
    validate_discovery_time,
)
from pyllmkit.protocols import AtomicCatalogPort

_Entity = TypeVar("_Entity", Model, InferenceProvider, Deployment)


def _canonical(value: object) -> object:
    """Full structural signature, bypassing entity identity-based __eq__.

    Only validated domain values are accepted. Sort unordered collections so
    the digest is deterministic across discovery order and registry replay.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return [
            "dataclass", type(value).__module__, type(value).__qualname__,
            [[item.name, _canonical(getattr(value, item.name))]
             for item in dataclass_fields(value)],
        ]
    if isinstance(value, Enum):
        return ["enum", type(value).__qualname__, value.name]
    if isinstance(value, (tuple, list)):
        return [type(value).__name__, [_canonical(item) for item in value]]
    if isinstance(value, (frozenset, set)):
        items = [_canonical(item) for item in value]
        return ["set", sorted(items, key=lambda item: json.dumps(item, sort_keys=True))]
    if isinstance(value, dict):
        pairs = [[_canonical(k), _canonical(v)] for k, v in value.items()]
        return ["mapping", sorted(
            pairs, key=lambda pair: json.dumps(pair[0], sort_keys=True)
        )]
    if value is None or type(value) in (bool, str, int, float):
        return [type(value).__name__, value]
    raise DomainValidationError("Unsupported catalog metadata value in preview")


def _candidate_digest(incoming: DiscoveryResult) -> str:
    """Private SHA-256 digest binds a preview to every candidate metadata field."""
    batches: tuple[
        tuple[str, tuple[Model | InferenceProvider | Deployment, ...]], ...
    ] = (
        ("provider", incoming.providers),
        ("model", incoming.models),
        ("deployment", incoming.deployments),
    )
    records = [
        [kind, item.id.value, _canonical(item)]
        for kind, values in batches
        for item in sorted(values, key=lambda entity: entity.id.value)
    ]
    wire = json.dumps(records, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return sha256(wire.encode("utf-8")).hexdigest()


def _field_differences(
    existing: Model | InferenceProvider | Deployment,
    incoming: Model | InferenceProvider | Deployment,
) -> tuple[str, ...]:
    """Use *full metadata*, never identity-only entity equality."""
    return tuple(
        sorted(
            field.name
            for field in dataclass_fields(existing)
            if getattr(existing, field.name) != getattr(incoming, field.name)
        )
    )


def _index(
    entries: tuple[_Entity, ...],
) -> dict[str, _Entity]:
    return {item.id.value: item for item in entries}


def _plan_entities(
    kind: str,
    incoming: tuple[_Entity, ...],
    current: dict[str, _Entity],
    origins: dict[tuple[str, str], CatalogProvenance],
    source: DiscoveryResult,
) -> tuple[
    dict[str, _Entity],
    list[CatalogChange],
    list[CatalogChange],
    list[RegistryConflict],
]:
    candidate = dict(current)
    added: list[CatalogChange] = []
    unchanged: list[CatalogChange] = []
    conflicts: list[RegistryConflict] = []
    for item in sorted(incoming, key=lambda x: x.id.value):
        ident = item.id.value
        origin = CatalogProvenance(kind, ident, source.source, source.observed_at)
        existing = current.get(ident)
        if existing is None:
            candidate[ident] = item
            origins[(kind, ident)] = origin
            added.append(CatalogChange(kind, ident, origin))
            continue
        differences = _field_differences(existing, item)
        if differences:
            conflicts.append(
                RegistryConflict(
                    kind, ident, differences, origin, origins.get((kind, ident))
                )
            )
        else:
            unchanged.append(CatalogChange(kind, ident, origin))
    return candidate, added, unchanged, conflicts


def _build_plan(
    snapshot: RegistrySnapshot,
    incoming: DiscoveryResult,
    policy: MergePolicy,
) -> tuple[MergePreview, RegistrySnapshot]:
    origins = {(o.entity_type, o.entity_id): o for o in snapshot.provenance}
    providers, pa, pu, pc = _plan_entities(
        "provider", incoming.providers, _index(snapshot.providers), origins, incoming
    )
    models, ma, mu, mc = _plan_entities(
        "model", incoming.models, _index(snapshot.models), origins, incoming
    )
    deployments, da, du, dc = _plan_entities(
        "deployment", incoming.deployments, _index(snapshot.deployments), origins, incoming
    )
    invalid: list[InvalidCatalogReference] = []
    for deployment in sorted(incoming.deployments, key=lambda dep: dep.id.value):
        if deployment.model_id.value not in models:
            invalid.append(
                InvalidCatalogReference(deployment.id.value, "model", deployment.model_id.value)
            )
        if deployment.provider_id is not None and deployment.provider_id.value not in providers:
            invalid.append(
                InvalidCatalogReference(
                    deployment.id.value, "provider", deployment.provider_id.value
                )
            )
    preview = MergePreview(
        revision=snapshot.revision,
        candidate_digest=_candidate_digest(incoming),
        policy=policy,
        source=incoming.source,
        observed_at=incoming.observed_at,
        additions=tuple(pa + ma + da),
        unchanged=tuple(pu + mu + du),
        conflicts=tuple(pc + mc + dc),
        invalid_references=tuple(
            sorted(invalid, key=lambda entry: (
                entry.deployment_id, entry.missing_type, entry.missing_id
            ))
        ),
    )
    candidate = RegistrySnapshot(
        revision=snapshot.revision,
        models=tuple(models[key] for key in sorted(models)),
        providers=tuple(providers[key] for key in sorted(providers)),
        deployments=tuple(deployments[key] for key in sorted(deployments)),
        provenance=tuple(origins[key] for key in sorted(origins)),
    )
    return preview, candidate


class CatalogMergeService:
    """Coordinate dry-run and explicit CAS apply over an AtomicCatalogPort."""

    __slots__ = ("_catalog",)

    def __init__(self, catalog: AtomicCatalogPort) -> None:
        if not isinstance(catalog, AtomicCatalogPort):
            raise DomainValidationError("catalog must implement AtomicCatalogPort")
        self._catalog = catalog

    def preview(
        self,
        incoming: DiscoveryResult,
        *,
        now: datetime,
        max_future_skew: timedelta = timedelta(0),
        policy: MergePolicy = MergePolicy.FAIL_ON_CONFLICT,
    ) -> MergePreview:
        if not isinstance(policy, MergePolicy):
            raise DomainValidationError("unsupported MergePolicy")
        validate_discovery_time(incoming, now=now, max_future_skew=max_future_skew)
        return _build_plan(self._catalog.snapshot(), incoming, policy)[0]

    def apply(
        self,
        incoming: DiscoveryResult,
        preview: MergePreview,
        *,
        now: datetime,
        max_future_skew: timedelta = timedelta(0),
    ) -> MergeResult:
        """Apply only an exact previously previewed, conflict-free batch."""
        if not isinstance(preview, MergePreview):
            raise DomainValidationError("apply requires MergePreview")
        validate_discovery_time(incoming, now=now, max_future_skew=max_future_skew)
        current = self._catalog.snapshot()
        if current.revision != preview.revision:
            raise RegistryStaleSnapshotError("Catalog changed after preview")
        expected, candidate = _build_plan(current, incoming, preview.policy)
        if preview != expected:
            raise RegistryStaleSnapshotError("Preview does not match current candidates")
        if not preview.can_apply:
            raise RegistryMergeRejectedError("Merge has conflicts or invalid references")
        if preview.no_op:
            return MergeResult(preview, applied=False, revision=current.revision)
        self._catalog.commit_snapshot(candidate, expected_revision=current.revision)
        return MergeResult(preview, applied=True, revision=current.revision + 1)
