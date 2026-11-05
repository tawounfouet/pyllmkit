"""P6-AC-049..056 integration and architecture checks for Registry & Discovery.

Acceptance labels here describe current implemented behavior. Formal gate GO
requires review, ordered merges and CI on the exact final main SHA.
"""

import ast
import importlib.metadata
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

import pyllmkit
from pyllmkit.adapters.registry import InMemoryCatalog, StaticDiscoverySource
from pyllmkit.application.registry import CatalogMergeService, DeploymentResolver
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId, ModelTarget
from pyllmkit.domain.models import (
    Model,
    ModelFamily,
    ModelId,
    ModelIdentity,
    model_from_dict,
    model_to_dict,
)
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    DiscoveryResult,
    MetadataSource,
    MetadataSourceKind,
    RegistryMergeRejectedError,
)
from pyllmkit.protocols import (
    AtomicCatalogPort,
    DeploymentRegistryPort,
    DiscoverySourcePort,
    ModelRegistryPort,
    ProviderCatalogPort,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 11, 5, 20, tzinfo=UTC)


def test_ac049_offline_end_to_end_import_search_resolve_with_three_port_integration() -> None:
    model = Model(ModelId("demo"), ModelIdentity(ModelFamily("demo")))
    provider = InferenceProvider(ProviderId("p"), "Fixture host")
    deployment = Deployment(
        DeploymentId("d"), model.id, provider.id, status=DeploymentStatus.AVAILABLE
    )
    source = StaticDiscoverySource(DiscoveryResult(
        MetadataSource(MetadataSourceKind.FIXTURE, "integration"), NOW,
        models=(model,), providers=(provider,), deployments=(deployment,),
    ))
    catalog = InMemoryCatalog()
    merger = CatalogMergeService(catalog)
    assert isinstance(source, DiscoverySourcePort)
    assert isinstance(catalog, AtomicCatalogPort)
    assert isinstance(catalog.models, ModelRegistryPort)
    assert isinstance(catalog.providers, ProviderCatalogPort)
    assert isinstance(catalog.deployments, DeploymentRegistryPort)
    preview = merger.preview(source.discover(), now=NOW)
    assert catalog.models.get(model.id) is None
    assert merger.apply(source.discover(), preview, now=NOW).applied
    selected = DeploymentResolver(
        catalog.models, catalog.deployments, catalog.providers
    ).resolve(ModelTarget(model.id))
    assert selected.deployment.id == deployment.id
    assert selected.report.selected_id == deployment.id


def test_ac050_explicit_public_api_does_not_require_provider_sdk() -> None:
    from pyllmkit.domain.registry import (
        CapabilityResolver,
        CatalogProvenance,
        DeploymentRequirement,
        LimitResolver,
        MergePolicy,
        ModelQuery,
    )

    assert CapabilityResolver is not None
    assert LimitResolver is not None
    assert CatalogProvenance is not None
    assert DeploymentRequirement is not None
    assert ModelQuery is not None
    assert MergePolicy.FAIL_ON_CONFLICT.value == "fail_on_conflict"
    package = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "dependencies = []" in package
    assert 'requires-python = ">=3.11"' in package


def test_ac051_domain_registry_import_fitness_no_adapters_application_or_network() -> None:
    domain = ROOT / "src/pyllmkit/domain/registry"
    modules = tuple(sorted(domain.glob("*.py")))
    assert len(modules) >= 6
    forbidden = (
        "pyllmkit.adapters", "pyllmkit.application", "requests", "httpx", "urllib",
        "socket", "openai", "anthropic", "boto3",
    )
    for path in modules:
        source = ast.parse(path.read_text(encoding="utf-8"))
        imported: list[str] = []
        for node in ast.walk(source):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.append(node.module)
        assert not any(
            module == blocked or module.startswith(blocked + ".")
            for module in imported for blocked in forbidden
        ), f"Invalid architecture dependency in {path.name}"


def test_ac052_rejected_merge_preserves_privacy_and_original_metadata() -> None:
    original = Model(
        ModelId("m"), ModelIdentity(ModelFamily("demo"))
    )
    catalog = InMemoryCatalog()
    catalog.models.register(original)
    service = CatalogMergeService(catalog)
    changed = Model(
        ModelId("m"), ModelIdentity(ModelFamily("other"))
    )
    batch = DiscoveryResult(
        MetadataSource(MetadataSourceKind.FIXTURE, "private-source-label"), NOW,
        models=(changed,),
    )
    preview = service.preview(batch, now=NOW)
    assert not preview.can_apply and preview.conflicts[0].changed_fields == ("identity",)
    with pytest.raises(RegistryMergeRejectedError) as failed:
        service.apply(batch, preview, now=NOW)
    assert "private-source-label" not in str(failed.value)
    assert "private-source-label" not in repr(preview)
    assert catalog.models.get(original.id) is original


def test_ac053_legacy_model_json_v1_remains_independent_of_p6_registry() -> None:
    model = Model(ModelId("regression"), ModelIdentity(ModelFamily("sample")))
    payload = model_to_dict(model)
    assert model_from_dict(payload) == model
    catalog = InMemoryCatalog()
    catalog.models.register(model)
    assert model_to_dict(catalog.models.get(model.id)) == payload  # type: ignore[arg-type]
    assert "provider_id" not in payload
    assert catalog.snapshot().revision == 1


def test_ac054_snapshot_replay_noop_without_side_effects() -> None:
    catalog = InMemoryCatalog()
    service = CatalogMergeService(catalog)
    batch = DiscoveryResult(
        MetadataSource(MetadataSourceKind.INTERNAL, "replay-source"), NOW,
        providers=(InferenceProvider(ProviderId("p"), "Fixture"),),
    )
    first = service.preview(batch, now=NOW)
    assert first.can_apply and len(first.additions) == 1
    service.apply(batch, first, now=NOW)
    initial = catalog.snapshot()
    replay = service.preview(batch, now=NOW)
    assert replay.no_op
    assert not service.apply(batch, replay, now=NOW).applied
    assert catalog.snapshot() == initial


def test_ac055_package_version_and_python_distribution_constraints_remain_stable() -> None:
    assert pyllmkit.__version__ == "0.1.0a2"
    assert importlib.metadata.version("pyllmkit") == "0.1.0a2"
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0a2"' in pyproject
    assert "setuptools" in pyproject
    assert "pyllmkit*" in pyproject


def test_ac056_56_unique_acceptance_labels_and_six_example_files_present() -> None:
    cases = tuple(sorted((ROOT / "tests/acceptance").glob("test_p6_l6*.py")))
    assert len(cases) == 7
    names: set[int] = set()
    for path in cases:
        source = path.read_text(encoding="utf-8")
        names.update(
            int(found) for found in re.findall(r"^def test_ac(\d{3})_", source, re.MULTILINE)
        )
    assert names == set(range(1, 57))
    for index in range(23, 29):
        matches = tuple((ROOT / "examples").glob(f"{index:02d}_*.py"))
        assert len(matches) == 1
    assert (ROOT / "docs/quality/PHASE_6_TRACEABILITY.md").exists()
    assert (ROOT / "docs/quality/P6_G7_IMPLEMENTATION_PRECHECK.md").exists()


def test_malformed_catalog_merge_input_is_explicitly_rejected() -> None:
    catalog = InMemoryCatalog()
    with pytest.raises(DomainValidationError):
        CatalogMergeService(catalog).preview("raw", now=NOW)  # type: ignore[arg-type]
