"""P6-AC-033..040: explicit, deterministic, provider-free serving selection."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.registry import DeploymentResolver
from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import (
    DeploymentId,
    DeploymentTarget,
    EndpointId,
    EndpointTarget,
    ModelTarget,
)
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import (
    AmbiguousDeploymentError,
    CapabilityMatchMode,
    DeploymentNotFoundError,
    DeploymentRequirement,
    ModelNotFoundError,
    NoCompatibleDeploymentError,
)

TOOLS = CapabilityId("tool_calling")
TEXT = Modality("text")
IMAGE = Modality("image")


def _caps(level: SupportLevel | None) -> CapabilitySet:
    return CapabilitySet((
        Capability(TOOLS, CapabilitySupport(
            level,
            notes="partial interface" if level is SupportLevel.PARTIAL else None,
        )),
    ))


def _modalities(
    inputs: frozenset[Modality] | None = frozenset((TEXT,)),
    outputs: frozenset[Modality] | None = frozenset((TEXT,)),
) -> ModalitySet:
    return ModalitySet(inputs, outputs)


def _catalog(
    *identifiers: str,
    model_support: SupportLevel | None = SupportLevel.NATIVE,
    provider_support: SupportLevel | None = SupportLevel.NATIVE,
    deployment_support: SupportLevel | None = SupportLevel.NATIVE,
    model_limits: ModelLimits | None = ModelLimits(context_window=128_000),
    provider_limits: ModelLimits | None = ModelLimits(context_window=128_000),
    deployment_limits: ModelLimits | None = ModelLimits(context_window=64_000),
    statuses: tuple[DeploymentStatus, ...] | None = None,
) -> InMemoryCatalog:
    catalog = InMemoryCatalog()
    catalog.models.register(Model(
        ModelId("m"), ModelIdentity(ModelFamily("llama")),
        limits=model_limits, modalities=_modalities(), capabilities=_caps(model_support),
    ))
    catalog.providers.register(InferenceProvider(
        ProviderId("p"), "Provider",
        capabilities=_caps(provider_support), modalities=_modalities(),
        limits=provider_limits,
    ))
    for i, did in enumerate(identifiers):
        catalog.deployments.register(Deployment(
            DeploymentId(did), ModelId("m"), ProviderId("p"),
            status=statuses[i] if statuses is not None else DeploymentStatus.AVAILABLE,
            capabilities=_caps(deployment_support), modalities=_modalities(),
            limits=deployment_limits, region="eu", runtime="vllm",
        ))
    return catalog


def _resolver(catalog: InMemoryCatalog) -> DeploymentResolver:
    return DeploymentResolver(catalog.models, catalog.deployments, catalog.providers)


def test_ac033_one_eligible_model_deployment_is_selected_with_evidence() -> None:
    catalog = _catalog("d1")
    result = _resolver(catalog).resolve(
        ModelTarget(ModelId("m")),
        DeploymentRequirement(
            required_capabilities=(TOOLS,),
            required_input_modalities=frozenset((TEXT,)),
            required_output_modalities=frozenset((TEXT,)),
            min_context_window=32_000,
        ),
    )
    assert result.deployment.id == DeploymentId("d1")
    assert result.report.selected_id == DeploymentId("d1")
    assert result.report.eligible == (DeploymentId("d1"),)
    assert result.report.rejected == ()
    assert result.capabilities.capabilities.supports(TOOLS)
    assert result.limits.limits.context_window == 64_000
    assert catalog.deployments.get(DeploymentId("d1")) is result.deployment


def test_ac034_no_candidate_produces_typed_no_compatible_report() -> None:
    catalog = _catalog()
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(ModelTarget(ModelId("m")))
    assert raised.value.report is not None
    assert raised.value.report.considered == ()
    assert raised.value.report.selected_id is None


def test_ac034_missing_model_and_exact_deployment_are_distinct() -> None:
    catalog = _catalog("d1")
    with pytest.raises(ModelNotFoundError):
        _resolver(catalog).resolve(ModelTarget(ModelId("absent")))
    with pytest.raises(DeploymentNotFoundError):
        _resolver(catalog).resolve(DeploymentTarget(DeploymentId("absent")))


def test_ac035_multiple_eligible_deployments_are_ambiguous_never_first() -> None:
    catalog = _catalog("z", "a")
    with pytest.raises(AmbiguousDeploymentError) as raised:
        _resolver(catalog).resolve(ModelTarget(ModelId("m")))
    report = raised.value.report
    assert report is not None
    assert report.considered == (DeploymentId("a"), DeploymentId("z"))
    assert report.eligible == report.considered
    assert report.selected_id is None
    assert report.rejected == ()


def test_ac036_provider_region_runtime_filters_are_hard_constraints() -> None:
    catalog = _catalog("a", "b")
    dep_b = catalog.deployments.get(DeploymentId("b"))
    assert dep_b is not None
    catalog.deployments.remove(dep_b.id)
    catalog.deployments.register(Deployment(
        dep_b.id, dep_b.model_id, dep_b.provider_id, status=dep_b.status,
        region="us", runtime="ollama", capabilities=dep_b.capabilities,
        modalities=dep_b.modalities, limits=dep_b.limits,
    ))
    result = _resolver(catalog).resolve(
        ModelTarget(ModelId("m")),
        DeploymentRequirement(provider_id=ProviderId("p"), region="us", runtime="ollama"),
    )
    assert result.deployment.id == DeploymentId("b")
    assert result.report.rejected[0].deployment_id == DeploymentId("a")
    assert "REGION_MISMATCH" in result.report.rejected[0].reasons
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")),
            DeploymentRequirement(provider_id=ProviderId("unlisted")),
        )
    assert raised.value.report is not None
    assert len(raised.value.report.rejected) == 2


def test_ac037_unknown_capability_fails_strict_selection() -> None:
    catalog = _catalog("d", deployment_support=None)
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")),
            DeploymentRequirement(required_capabilities=(TOOLS,)),
        )
    assert raised.value.report is not None
    assert "CAPABILITY_NOT_NATIVE" in raised.value.report.rejected[0].reasons


def test_ac037_usable_mode_explicitly_accepts_partial_or_emulated() -> None:
    catalog = _catalog("d", deployment_support=SupportLevel.PARTIAL)
    with pytest.raises(NoCompatibleDeploymentError):
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")),
            DeploymentRequirement(required_capabilities=(TOOLS,)),
        )
    result = _resolver(catalog).resolve(
        ModelTarget(ModelId("m")),
        DeploymentRequirement(
            required_capabilities=(TOOLS,), capability_mode=CapabilityMatchMode.USABLE
        ),
    )
    assert result.deployment.id == DeploymentId("d")
    assert not result.capabilities.get(TOOLS).fully_native  # type: ignore[union-attr]
    emulated = _catalog("d", deployment_support=SupportLevel.EMULATED)
    assert _resolver(emulated).resolve(
        ModelTarget(ModelId("m")),
        DeploymentRequirement(required_capabilities=(TOOLS,), capability_mode=CapabilityMatchMode.USABLE),
    ).deployment.id == DeploymentId("d")


def test_ac038_declared_status_is_required_by_default_not_live_health() -> None:
    catalog = _catalog("down", "unknown", "up", statuses=(
        DeploymentStatus.UNAVAILABLE, DeploymentStatus.UNKNOWN, DeploymentStatus.AVAILABLE,
    ))
    result = _resolver(catalog).resolve(ModelTarget(ModelId("m")))
    assert result.deployment.id == DeploymentId("up")
    assert tuple(x.deployment_id.value for x in result.report.rejected) == ("down", "unknown")
    assert all("STATUS_NOT_AVAILABLE" in x.reasons for x in result.report.rejected)


def test_ac038_opt_out_of_availability_is_explicit_and_can_create_ambiguity() -> None:
    catalog = _catalog("down", "up", statuses=(
        DeploymentStatus.UNAVAILABLE, DeploymentStatus.AVAILABLE
    ))
    with pytest.raises(AmbiguousDeploymentError):
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")), DeploymentRequirement(require_available=False)
        )


def test_ac039_exact_target_is_not_redirected_or_silently_fallback() -> None:
    catalog = _catalog("down", "up", statuses=(
        DeploymentStatus.UNAVAILABLE, DeploymentStatus.AVAILABLE
    ))
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(DeploymentTarget(DeploymentId("down")))
    assert raised.value.report is not None
    assert raised.value.report.considered == (DeploymentId("down"),)
    assert raised.value.report.eligible == ()
    assert _resolver(catalog).resolve(
        DeploymentTarget(DeploymentId("up")),
    ).deployment.id == DeploymentId("up")


def test_ac040_pure_reproducible_order_independent_of_registry_insertion() -> None:
    left, right = _catalog("b", "a"), _catalog("a", "b")
    before = left.deployments.list()
    with pytest.raises(AmbiguousDeploymentError) as a:
        _resolver(left).resolve(ModelTarget(ModelId("m")))
    with pytest.raises(AmbiguousDeploymentError) as b:
        _resolver(right).resolve(ModelTarget(ModelId("m")))
    assert a.value.report == b.value.report
    assert left.deployments.list() == before


def test_context_bound_must_be_known_confirmed_and_sufficient() -> None:
    good = _catalog("d", deployment_limits=ModelLimits(context_window=10_000))
    result = _resolver(good).resolve(
        ModelTarget(ModelId("m")), DeploymentRequirement(min_context_window=8_000)
    )
    assert result.limits.limits.context_window == 10_000
    small = _catalog("d", deployment_limits=ModelLimits(context_window=5_000))
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(small).resolve(
            ModelTarget(ModelId("m")), DeploymentRequirement(min_context_window=8_000)
        )
    assert "CONTEXT_TOO_SMALL" in raised.value.report.rejected[0].reasons  # type: ignore[union-attr]
    provisional = _catalog("d", provider_limits=None)
    with pytest.raises(NoCompatibleDeploymentError) as raised2:
        _resolver(provisional).resolve(
            ModelTarget(ModelId("m")), DeploymentRequirement(min_context_window=8_000)
        )
    assert "CONTEXT_PROVISIONAL" in raised2.value.report.rejected[0].reasons  # type: ignore[union-attr]


def test_context_fully_unknown_rejected_when_requested() -> None:
    catalog = _catalog(
        "d", model_limits=None, deployment_limits=None, provider_limits=None
    )
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")), DeploymentRequirement(min_context_window=1)
        )
    assert "CONTEXT_UNKNOWN" in raised.value.report.rejected[0].reasons  # type: ignore[union-attr]


def test_directional_modality_requires_every_applicable_layer() -> None:
    catalog = _catalog("d")
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")),
            DeploymentRequirement(required_input_modalities=frozenset((IMAGE,))),
        )
    assert "INPUT_MODALITY_NOT_CONFIRMED" in raised.value.report.rejected[0].reasons  # type: ignore[union-attr]
    with pytest.raises(NoCompatibleDeploymentError) as raised2:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")),
            DeploymentRequirement(required_output_modalities=frozenset((IMAGE,))),
        )
    assert "OUTPUT_MODALITY_NOT_CONFIRMED" in raised2.value.report.rejected[0].reasons  # type: ignore[union-attr]


def test_requirements_are_immutable_and_validation_rejects_wrong_types() -> None:
    requirement = DeploymentRequirement(
        required_capabilities=(CapabilityId("zeta"), TOOLS)
    )
    assert requirement.required_capabilities == (TOOLS, CapabilityId("zeta"))
    with pytest.raises(FrozenInstanceError):
        requirement.region = "new"  # type: ignore[misc]
    bad = (
        {"provider_id": "p"}, {"region": " "}, {"runtime": 42},
        {"require_available": "yes"}, {"required_capabilities": [TOOLS]},
        {"required_capabilities": (TOOLS, TOOLS)},
        {"required_capabilities": ("raw",)}, {"capability_mode": "usable"},
        {"required_input_modalities": {TEXT}},
        {"required_output_modalities": frozenset(("raw",))},
        {"min_context_window": -1}, {"min_context_window": True},
    )
    for item in bad:
        with pytest.raises(DomainValidationError):
            DeploymentRequirement(**item)  # type: ignore[arg-type]


def test_wrong_targets_or_requirements_never_get_coerced() -> None:
    catalog = _catalog("d")
    resolver = _resolver(catalog)
    with pytest.raises(DomainValidationError):
        resolver.resolve(cast(ModelTarget, "m"))
    with pytest.raises(DomainValidationError):
        resolver.resolve(cast(ModelTarget, EndpointTarget(EndpointId("endpoint"))))
    with pytest.raises(DomainValidationError):
        resolver.resolve(ModelTarget(ModelId("m")), cast(DeploymentRequirement, "any"))


def test_rejection_reasons_do_not_expose_model_or_provider_names() -> None:
    catalog = _catalog("d")
    with pytest.raises(NoCompatibleDeploymentError) as raised:
        _resolver(catalog).resolve(
            ModelTarget(ModelId("m")), DeploymentRequirement(region="secret-region")
        )
    assert "secret-region" not in str(raised.value)
    assert "REGION_MISMATCH" in raised.value.report.rejected[0].reasons  # type: ignore[union-attr]
