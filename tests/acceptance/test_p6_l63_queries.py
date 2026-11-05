"""P6-AC-017..024: strict domain queries over in-memory registry snapshots."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.adapters.registry import InMemoryCatalog
from pyllmkit.application.registry import CatalogSearchService
from pyllmkit.domain.capabilities import (
    Capability, CapabilityId, CapabilitySet, CapabilitySupport, SupportLevel,
)
from pyllmkit.domain.deployments import Deployment, DeploymentStatus
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.modalities import Modality, ModalitySet
from pyllmkit.domain.models import (
    Model, ModelFamily, ModelId, ModelIdentity, ModelLimits, ModelVariant,
    ProviderModelRef,
)
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import CapabilityMatchMode, DeploymentQuery, ModelQuery


TEXT = Modality("text")
IMAGE = Modality("image")
CHAT = CapabilityId("chat")
TOOLS = CapabilityId("tool_calling")


def _caps(level: SupportLevel | None, name: CapabilityId = TOOLS) -> CapabilitySet:
    return CapabilitySet((Capability(name, CapabilitySupport(level, notes="subset")),))


def _model(
    mid: str, *, family: str = "llama", variant: str = "base",
    developer: str | None = None, provider: str | None = None,
    support: SupportLevel | None = None, context: int | None = None,
    inputs: frozenset[Modality] | None = None,
    outputs: frozenset[Modality] | None = None,
) -> Model:
    model_id = ModelId(mid)
    return Model(
        model_id,
        ModelIdentity(ModelFamily(family), variant=ModelVariant(variant), developer=developer),
        limits=ModelLimits(context_window=context) if context is not None else None,
        capabilities=_caps(support),
        modalities=ModalitySet(inputs, outputs),
        provider_refs=(ProviderModelRef(provider, model_id, "vendor-alias"),)
        if provider is not None else (),
    )


def _deployment(
    did: str, *, status: DeploymentStatus = DeploymentStatus.UNKNOWN,
    region: str | None = None, runtime: str | None = None,
    model: str = "m", provider: str | None = "p",
    support: SupportLevel | None = None,
    inputs: frozenset[Modality] | None = None,
    outputs: frozenset[Modality] | None = None,
) -> Deployment:
    return Deployment(
        DeploymentId(did), ModelId(model),
        ProviderId(provider) if provider is not None else None,
        status=status, region=region, runtime=runtime,
        capabilities=_caps(support) if support is not None else None,
        modalities=ModalitySet(inputs, outputs) if inputs is not None or outputs is not None
        else None,
    )


def test_ac017_model_family_search_keeps_distinct_variants_and_ids() -> None:
    registry = InMemoryCatalog()
    for model in (
        _model("llama-b", variant="large"), _model("other", family="qwen"),
        _model("llama-a", variant="small"),
    ):
        registry.models.register(model)
    query = ModelQuery(family=ModelFamily("llama"))
    found = registry.models.find(query)
    assert tuple(item.id.value for item in found) == ("llama-a", "llama-b")
    assert found[0].identity.variant != found[1].identity.variant
    assert registry.models.list()[0].id.value == "llama-a"


def test_ac018_native_mode_vs_explicit_usable_keeps_unknown_out() -> None:
    catalog = InMemoryCatalog()
    for name, level in (
        ("native", SupportLevel.NATIVE), ("emulated", SupportLevel.EMULATED),
        ("partial", SupportLevel.PARTIAL), ("unsupported", SupportLevel.UNSUPPORTED),
        ("unknown", None),
    ):
        catalog.models.register(_model(name, support=level))
    native = catalog.models.find(ModelQuery(required_capabilities=(TOOLS,)))
    usable = catalog.models.find(ModelQuery(
        required_capabilities=(TOOLS,), capability_mode=CapabilityMatchMode.USABLE
    ))
    assert tuple(m.id.value for m in native) == ("native",)
    assert tuple(m.id.value for m in usable) == ("emulated", "native", "partial")
    assert catalog.models.find(ModelQuery(required_capabilities=(CHAT,))) == ()


def test_ac019_input_and_output_modalities_must_match_independently() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("in-image", inputs=frozenset((TEXT, IMAGE)), outputs=frozenset((TEXT,))))
    catalog.models.register(_model("out-image", inputs=frozenset((TEXT,)), outputs=frozenset((IMAGE,))))
    catalog.models.register(_model("no-declaration"))
    query = ModelQuery(required_input_modalities=frozenset((IMAGE,)))
    assert tuple(m.id.value for m in catalog.models.find(query)) == ("in-image",)
    assert tuple(m.id.value for m in catalog.models.find(
        ModelQuery(required_output_modalities=frozenset((IMAGE,)))
    )) == ("out-image",)
    assert catalog.models.find(ModelQuery(
        required_input_modalities=frozenset((IMAGE,)),
        required_output_modalities=frozenset((IMAGE,)),
    )) == ()


def test_ac020_provider_filter_matches_verified_alias_without_rewriting_model_id() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("canonical", provider="groq"))
    catalog.models.register(_model("other", provider="bedrock"))
    catalog.models.register(_model("without"))
    matches = catalog.models.find(ModelQuery(provider_id=ProviderId("groq")))
    assert len(matches) == 1 and matches[0].id == ModelId("canonical")
    assert catalog.models.find(ModelQuery(provider_id=ProviderId("openai"))) == ()


def test_ac021_context_limit_requires_known_declared_value() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("unknown"))
    catalog.models.register(_model("small", context=1024))
    catalog.models.register(_model("large", context=8192))
    assert tuple(m.id.value for m in catalog.models.find(
        ModelQuery(min_context_window=4096)
    )) == ("large",)


def test_ac022_deployment_filters_status_region_runtime_model_provider() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.providers.register(InferenceProvider(ProviderId("p"), "Provider"))
    catalog.providers.register(InferenceProvider(ProviderId("q"), "Another"))
    for deployment in (
        _deployment("d2", status=DeploymentStatus.AVAILABLE, region="eu", runtime="vllm"),
        _deployment("d1", status=DeploymentStatus.AVAILABLE, region="eu", runtime="vllm"),
        _deployment("d3", status=DeploymentStatus.UNAVAILABLE, region="eu", runtime="vllm"),
        _deployment("d4", status=DeploymentStatus.AVAILABLE, region="us", runtime="vllm"),
        _deployment("d5", status=DeploymentStatus.AVAILABLE, region="eu", runtime="ollama"),
        _deployment("d6", status=DeploymentStatus.AVAILABLE, region="eu", runtime="vllm", provider="q"),
    ):
        catalog.deployments.register(deployment)
    query = DeploymentQuery(
        model_id=ModelId("m"), provider_id=ProviderId("p"),
        status=DeploymentStatus.AVAILABLE, region="eu", runtime="vllm",
    )
    assert tuple(d.id.value for d in catalog.deployments.find(query)) == ("d1", "d2")
    assert tuple(d.id.value for d in catalog.deployments.find(
        DeploymentQuery(deployment_id=DeploymentId("d1"))
    )) == ("d1",)


def test_ac023_conjunctive_search_is_stable_readonly_and_no_mutation() -> None:
    catalog = InMemoryCatalog()
    for model in (
        _model("z", family="llama", developer="Meta", provider="p",
               support=SupportLevel.NATIVE, context=8192, inputs=frozenset((TEXT,))),
        _model("a", family="llama", developer="Meta", provider="p",
               support=SupportLevel.NATIVE, context=8192, inputs=frozenset((TEXT,))),
        _model("x", family="llama", developer="Else", provider="p",
               support=SupportLevel.NATIVE, context=8192, inputs=frozenset((TEXT,))),
    ):
        catalog.models.register(model)
    svc = CatalogSearchService(catalog.models, catalog.deployments)
    query = ModelQuery(
        family=ModelFamily("llama"), developer="Meta", provider_id=ProviderId("p"),
        required_capabilities=(TOOLS,), required_input_modalities=frozenset((TEXT,)),
        min_context_window=8192,
    )
    before = catalog.models.list()
    assert tuple(m.id.value for m in svc.find_models(query)) == ("a", "z")
    assert svc.find_models(query) == svc.find_models(query)
    assert catalog.models.list() == before
    with pytest.raises(FrozenInstanceError):
        query.developer = "modified"  # type: ignore[misc]
    with pytest.raises(DomainValidationError):
        svc.find_models(cast(ModelQuery, "invalid"))


def test_ac024_unknown_deployment_capability_is_not_a_confirmed_match() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m", support=SupportLevel.NATIVE))
    catalog.providers.register(InferenceProvider(ProviderId("p"), "Provider"))
    catalog.deployments.register(_deployment("unknown", status=DeploymentStatus.AVAILABLE))
    catalog.deployments.register(_deployment(
        "native", status=DeploymentStatus.AVAILABLE, support=SupportLevel.NATIVE,
        inputs=frozenset((TEXT,)), outputs=frozenset((TEXT,)),
    ))
    svc = CatalogSearchService(catalog.models, catalog.deployments)
    query = DeploymentQuery(
        status=DeploymentStatus.AVAILABLE,
        required_capabilities=(TOOLS,),
        required_input_modalities=frozenset((TEXT,)),
    )
    assert tuple(d.id.value for d in svc.find_deployments(query)) == ("native",)
    assert svc.find_deployments(DeploymentQuery(runtime="undeclared")) == ()
    assert svc.find_models(ModelQuery(model_id=ModelId("not-registered"))) == ()


def test_declared_deployment_emulation_only_matches_usable_mode() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.deployments.register(_deployment("emulated", provider=None, support=SupportLevel.EMULATED))
    assert catalog.deployments.find(DeploymentQuery(required_capabilities=(TOOLS,))) == ()
    assert tuple(d.id.value for d in catalog.deployments.find(DeploymentQuery(
        required_capabilities=(TOOLS,), capability_mode=CapabilityMatchMode.USABLE,
    ))) == ("emulated",)


def test_deployment_directional_modalities_and_missing_declarations() -> None:
    catalog = InMemoryCatalog()
    catalog.models.register(_model("m"))
    catalog.deployments.register(_deployment("unknown", provider=None))
    catalog.deployments.register(_deployment(
        "image-in", provider=None, inputs=frozenset((IMAGE,)), outputs=frozenset((TEXT,))
    ))
    assert tuple(d.id.value for d in catalog.deployments.find(DeploymentQuery(
        required_input_modalities=frozenset((IMAGE,))
    ))) == ("image-in",)
    assert catalog.deployments.find(DeploymentQuery(
        required_output_modalities=frozenset((IMAGE,))
    )) == ()


def test_queries_validate_structural_types_no_coercion_or_duplicate_caps() -> None:
    for kwargs in (
        {"model_id": "raw"}, {"family": "llama"}, {"developer": " "},
        {"provider_id": "raw"}, {"capability_mode": "usable"},
        {"required_capabilities": [TOOLS]},
        {"required_capabilities": (TOOLS, TOOLS)},
        {"required_capabilities": ("raw",)},
        {"required_input_modalities": {TEXT}},
        {"required_output_modalities": frozenset(("raw",))},
        {"min_context_window": -1}, {"min_context_window": True},
    ):
        with pytest.raises(DomainValidationError):
            ModelQuery(**kwargs)  # type: ignore[arg-type]
    for kwargs in (
        {"deployment_id": "raw"}, {"model_id": "raw"}, {"provider_id": "raw"},
        {"status": "available"}, {"region": " "}, {"runtime": 42},
        {"capability_mode": "usable"}, {"required_capabilities": [TOOLS]},
        {"required_input_modalities": [TEXT]},
        {"required_output_modalities": frozenset(("raw",))},
    ):
        with pytest.raises(DomainValidationError):
            DeploymentQuery(**kwargs)  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError):
        ModelQuery()(cast(Model, "invalid"))
    with pytest.raises(DomainValidationError):
        DeploymentQuery()(cast(Deployment, "invalid"))


def test_required_capability_order_is_canonical() -> None:
    query = ModelQuery(required_capabilities=(TOOLS, CHAT))
    assert query.required_capabilities == (CHAT, TOOLS)
