"""P6-AC-041..048: offline source, provenance and fail-closed batch merge."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from pyllmkit.adapters.registry import InMemoryCatalog, StaticDiscoverySource
from pyllmkit.application.registry import CatalogMergeService
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    CatalogProvenance,
    DiscoveryResult,
    MergePolicy,
    MetadataSource,
    MetadataSourceKind,
    RegistryConflict,
    RegistryMergeRejectedError,
    RegistrySnapshot,
    RegistryStaleSnapshotError,
)
from pyllmkit.protocols import AtomicCatalogPort, DiscoverySourcePort

NOW = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)
SRC = MetadataSource(MetadataSourceKind.FIXTURE, "reference-catalog", "internal")


def _model(name: str = "m", *, context_window: int | None = None) -> Model:
    return Model(
        ModelId(name), ModelIdentity(ModelFamily("llama")),
        limits=ModelLimits(context_window=context_window),
    )


def _provider(name: str = "p", *, label: str = "Provider") -> InferenceProvider:
    return InferenceProvider(ProviderId(name), label)


def _deployment(
    name: str = "d", *, model: str = "m", provider: str | None = "p"
) -> Deployment:
    return Deployment(
        DeploymentId(name), ModelId(model),
        provider_id=ProviderId(provider) if provider is not None else None,
        status=DeploymentStatus.AVAILABLE,
    )


def _batch(
    *,
    models: tuple[Model, ...] = (),
    providers: tuple[InferenceProvider, ...] = (),
    deployments: tuple[Deployment, ...] = (),
    observed_at: datetime = NOW,
    source: MetadataSource = SRC,
) -> DiscoveryResult:
    return DiscoveryResult(
        source, observed_at, providers=providers, models=models, deployments=deployments
    )


def _full_batch() -> DiscoveryResult:
    return _batch(
        models=(_model(),),
        providers=(_provider(),),
        deployments=(_deployment(),),
    )


def test_ac041_static_source_is_typed_pure_and_never_registers_automatically() -> None:
    batch = _full_batch()
    source = StaticDiscoverySource(batch)
    catalog = InMemoryCatalog()
    assert isinstance(source, DiscoverySourcePort)
    assert source.discover() is batch
    assert source.discover() is batch
    assert catalog.models.list() == ()
    assert catalog.providers.list() == ()
    assert catalog.deployments.list() == ()
    assert batch.source.kind is MetadataSourceKind.FIXTURE
    assert batch.warnings == ()
    with pytest.raises(FrozenInstanceError):
        source.result = _batch()  # type: ignore[misc]
    with pytest.raises(DomainValidationError):
        StaticDiscoverySource(cast(DiscoveryResult, "raw"))


def test_ac042_time_is_utc_injected_and_future_skew_explicit() -> None:
    service = CatalogMergeService(InMemoryCatalog())
    batch = _batch(observed_at=NOW + timedelta(minutes=4))
    with pytest.raises(DomainValidationError, match="future skew"):
        service.preview(batch, now=NOW)
    preview = service.preview(batch, now=NOW, max_future_skew=timedelta(minutes=5))
    assert preview.no_op
    with pytest.raises(DomainValidationError, match="now"):
        service.preview(batch, now=NOW.replace(tzinfo=None))
    with pytest.raises(DomainValidationError, match="max_future_skew"):
        service.preview(batch, now=NOW, max_future_skew=timedelta(seconds=-1))
    with pytest.raises(DomainValidationError, match="observed_at"):
        _batch(observed_at=NOW.replace(tzinfo=None))


def test_ac043_import_three_kinds_with_origin_and_one_revision() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    before = catalog.snapshot()
    batch = _full_batch()
    preview = service.preview(batch, now=NOW)
    assert preview.can_apply and not preview.no_op
    assert catalog.snapshot() == before
    assert tuple((x.entity_type, x.entity_id) for x in preview.additions) == (
        ("provider", "p"), ("model", "m"), ("deployment", "d"),
    )
    result = service.apply(batch, preview, now=NOW)
    assert result.applied
    assert result.revision == 1
    assert catalog.snapshot().revision == 1
    assert len(catalog.providers.list()) == len(catalog.models.list()) == 1
    assert len(catalog.deployments.list()) == 1
    assert catalog.deployments.get(DeploymentId("d")).model_id == ModelId("m")  # type: ignore[union-attr]
    origins = catalog.snapshot().provenance
    assert len(origins) == 3
    assert all(item.source == SRC and item.observed_at == NOW for item in origins)
    assert ("model", "m") in tuple((x.entity_type, x.entity_id) for x in origins)


def test_ac044_preview_is_read_only_and_sorted_regardless_of_batch_order() -> None:
    batch = _batch(
        models=(_model("z"), _model("a")),
        providers=(_provider("p-z"), _provider("p-a")),
        deployments=(_deployment("z", model="z", provider="p-z"),
                     _deployment("a", model="a", provider="p-a")),
    )
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    preview = service.preview(batch, now=NOW)
    assert catalog.snapshot().revision == 0
    assert catalog.models.list() == ()
    assert tuple(item.entity_id for item in preview.additions) == (
        "p-a", "p-z", "a", "z", "a", "z"
    )
    assert service.preview(batch, now=NOW) == preview
    flipped = _batch(
        models=tuple(reversed(batch.models)),
        providers=tuple(reversed(batch.providers)),
        deployments=tuple(reversed(batch.deployments)),
    )
    assert service.preview(flipped, now=NOW) == preview


def test_ac045_model_collision_rejects_full_batch_not_identity_only() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m", context_window=100))
    original = catalog.snapshot()
    modified = _model("m", context_window=200)
    assert modified == _model("m", context_window=100)  # ID-based Model.__eq__
    batch = _batch(
        models=(modified,),
        providers=(_provider(),),
        deployments=(_deployment(),),
    )
    service = CatalogMergeService(catalog)
    preview = service.preview(batch, now=NOW)
    assert not preview.can_apply
    assert len(preview.conflicts) == 1
    conflict = preview.conflicts[0]
    assert isinstance(conflict, RegistryConflict)
    assert (conflict.entity_type, conflict.entity_id) == ("model", "m")
    assert conflict.changed_fields == ("limits",)
    assert conflict.existing_provenance is None
    assert conflict.incoming_provenance.source == SRC
    with pytest.raises(RegistryMergeRejectedError):
        service.apply(batch, preview, now=NOW)
    assert catalog.snapshot() == original
    assert catalog.providers.list() == ()
    assert catalog.deployments.list() == ()


def test_ac045_imported_record_conflict_preserves_both_sources() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    batch = _batch(providers=(_provider(),))
    service.apply(batch, service.preview(batch, now=NOW), now=NOW)
    source2 = MetadataSource(MetadataSourceKind.EXPORT, "second-catalog")
    incoming = _batch(
        providers=(_provider(label="Updated"),),
        source=source2,
        observed_at=NOW + timedelta(seconds=1),
    )
    preview = service.preview(incoming, now=NOW + timedelta(seconds=1))
    assert preview.conflicts[0].changed_fields == ("display_name",)
    assert preview.conflicts[0].existing_provenance is not None
    assert preview.conflicts[0].existing_provenance.source == SRC  # type: ignore[union-attr]
    assert preview.conflicts[0].incoming_provenance.source == source2
    with pytest.raises(RegistryMergeRejectedError):
        service.apply(incoming, preview, now=NOW + timedelta(seconds=1))
    assert catalog.providers.get(ProviderId("p")).display_name == "Provider"  # type: ignore[union-attr]


def test_ac046_missing_model_provider_references_reject_whole_batch() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    batch = _batch(
        providers=(_provider("new"),),
        models=(_model("known"),),
        deployments=(
            _deployment("broken", model="absent", provider="also-absent"),
            _deployment("valid", model="known", provider="new"),
        ),
    )
    preview = service.preview(batch, now=NOW)
    assert not preview.can_apply
    assert tuple((x.deployment_id, x.missing_type) for x in preview.invalid_references) == (
        ("broken", "model"), ("broken", "provider")
    )
    with pytest.raises(RegistryMergeRejectedError):
        service.apply(batch, preview, now=NOW)
    assert catalog.snapshot().revision == 0
    assert catalog.models.list() == ()
    assert catalog.providers.list() == ()
    assert catalog.deployments.list() == ()


def test_ac046_invalid_references_are_checked_on_candidate_copy_not_input_order() -> None:
    batch = _batch(
        deployments=(_deployment(),),
        models=(_model(),),
        providers=(_provider(),),
    )
    service = CatalogMergeService(InMemoryCatalog())
    assert service.preview(batch, now=NOW).can_apply


def test_ac047_idempotent_replay_is_no_op_and_preserves_original_provenance() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    first = _full_batch()
    result = service.apply(first, service.preview(first, now=NOW), now=NOW)
    assert result.applied
    snapshot = catalog.snapshot()
    second_source = MetadataSource(MetadataSourceKind.STATIC_FILE, "catalog-file")
    repeated = _batch(
        models=first.models, providers=first.providers, deployments=first.deployments,
        source=second_source, observed_at=NOW + timedelta(seconds=30),
    )
    preview2 = service.preview(repeated, now=NOW + timedelta(seconds=30))
    assert preview2.additions == ()
    assert len(preview2.unchanged) == 3
    assert preview2.no_op
    applied = service.apply(repeated, preview2, now=NOW + timedelta(seconds=30))
    assert not applied.applied
    assert applied.revision == snapshot.revision
    assert catalog.snapshot() == snapshot


def test_ac047_stale_preview_after_direct_registry_change_is_rejected() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    batch = _full_batch()
    preview = service.preview(batch, now=NOW)
    catalog.models.register(_model("other"))
    before = catalog.snapshot()
    with pytest.raises(RegistryStaleSnapshotError):
        service.apply(batch, preview, now=NOW)
    assert catalog.snapshot() == before
    assert catalog.providers.list() == ()


def test_ac047_preview_is_bound_to_exact_batch_and_policy() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    preview = service.preview(_full_batch(), now=NOW)
    changed = _batch(models=(_model("different"),))
    with pytest.raises(RegistryStaleSnapshotError):
        service.apply(changed, preview, now=NOW)
    with pytest.raises(DomainValidationError):
        service.preview(_full_batch(), now=NOW, policy=cast(MergePolicy, "overwrite"))
    with pytest.raises(DomainValidationError):
        service.apply(_full_batch(), cast(object, "not a preview"), now=NOW)  # type: ignore[arg-type]
    assert catalog.snapshot().revision == 0


def test_ac048_commutative_import_of_disjoint_batches_yields_same_catalog() -> None:
    a = _batch(
        models=(_model("a"),), providers=(_provider("pa"),),
        deployments=(_deployment("da", model="a", provider="pa"),),
    )
    b = _batch(
        models=(_model("b"),), providers=(_provider("pb"),),
        deployments=(_deployment("db", model="b", provider="pb"),),
    )
    left, right = InMemoryCatalog(), InMemoryCatalog()
    for catalog, batches in ((left, (a, b)), (right, (b, a))):
        svc = CatalogMergeService(catalog)
        for batch in batches:
            preview = svc.preview(batch, now=NOW)
            svc.apply(batch, preview, now=NOW)
    assert left.snapshot() == right.snapshot()
    assert len(left.snapshot().provenance) == 6


def test_ac048_invalid_batch_shapes_and_duplicates_rejected() -> None:
    for kwargs in (
        {"providers": [_provider()]},
        {"models": (_model(), _model())},
        {"deployments": (_deployment(), _deployment())},
        {"providers": (_provider(), _provider())},
        {"models": ("raw",)},
        {"warnings": ("",)},
        {"warnings": ["note"]},
        {"warnings": tuple("warning" for _ in range(33))},
    ):
        with pytest.raises(DomainValidationError):
            DiscoveryResult(SRC, NOW, **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad",
    ("", "  ", "https://example.org/catalog", "path?token=abc", "host@service",
     "token=secret", "control\nchar"),
)
def test_metadata_source_rejects_unsafe_references(bad: str) -> None:
    with pytest.raises(DomainValidationError):
        MetadataSource(MetadataSourceKind.FIXTURE, bad)


def test_metadata_source_rejects_invalid_kind_authority_and_wrong_timestamp() -> None:
    with pytest.raises(DomainValidationError):
        MetadataSource(cast(MetadataSourceKind, "HTTP"), "catalog")
    with pytest.raises(DomainValidationError):
        MetadataSource(MetadataSourceKind.FIXTURE, "catalog", authority="token=secret")
    with pytest.raises(DomainValidationError):
        CatalogProvenance("unknown", "m", SRC, NOW)
    with pytest.raises(DomainValidationError):
        CatalogProvenance("model", "", SRC, NOW)
    with pytest.raises(DomainValidationError):
        CatalogProvenance("model", "m", SRC, NOW.replace(tzinfo=None))


def test_snapshot_rejects_invalid_revision_typed_tuples_and_duplicates() -> None:
    for kwargs in (
        {"revision": True}, {"revision": -1}, {"models": [_model()]},
        {"models": (_model(), _model())},
        {"providers": ("raw",)},
        {"deployments": (_deployment(), _deployment())},
        {"provenance": ("raw",)},
        {"provenance": (
            CatalogProvenance("model", "m", SRC, NOW),
            CatalogProvenance("model", "m", SRC, NOW),
        )},
    ):
        values: dict[str, object] = {
            "revision": 0, "models": (), "providers": (), "deployments": (),
        }
        values.update(kwargs)
        with pytest.raises(DomainValidationError):
            RegistrySnapshot(**values)  # type: ignore[arg-type]


def test_registry_snapshot_atomic_commit_validates_references_and_revision() -> None:
    catalog = InMemoryCatalog()
    assert isinstance(catalog, AtomicCatalogPort)
    bad = RegistrySnapshot(0, (), (), (_deployment(),))
    with pytest.raises(Exception, match="missing references"):
        catalog.commit_snapshot(bad, expected_revision=0)
    assert catalog.snapshot().revision == 0
    with pytest.raises(RegistryStaleSnapshotError):
        catalog.commit_snapshot(RegistrySnapshot(0, (), (), ()), expected_revision=1)
    with pytest.raises(DomainValidationError):
        catalog.commit_snapshot(RegistrySnapshot(0, (), (), ()), expected_revision=True)
    with pytest.raises(DomainValidationError):
        catalog.commit_snapshot(cast(RegistrySnapshot, "bad"), expected_revision=0)


def test_catalog_direct_removal_clears_imported_record_provenance() -> None:
    catalog = InMemoryCatalog()
    svc = CatalogMergeService(catalog)
    full = _full_batch()
    svc.apply(full, svc.preview(full, now=NOW), now=NOW)
    assert catalog.deployments.remove(DeploymentId("d"))
    assert catalog.models.remove(ModelId("m"))
    assert catalog.providers.remove(ProviderId("p"))
    assert catalog.snapshot().provenance == ()
    assert catalog.snapshot().revision == 4


def test_failure_does_not_disclose_raw_source_reference() -> None:
    source = MetadataSource(MetadataSourceKind.INTERNAL, "sensitive-local-label")
    catalog = InMemoryCatalog()
    svc = CatalogMergeService(catalog)
    catalog.models.register(_model(context_window=1))
    batch = _batch(models=(_model(context_window=2),), source=source)
    preview = svc.preview(batch, now=NOW)
    with pytest.raises(RegistryMergeRejectedError) as exc:
        svc.apply(batch, preview, now=NOW)
    assert "sensitive-local-label" not in str(exc.value)
    assert "sensitive-local-label" not in repr(preview)
