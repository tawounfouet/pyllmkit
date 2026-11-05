"""P6-AC-025..032: restrictive, evidence-rich provider-free resolution."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityConstraint,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.deployments import Deployment
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.inference import DeploymentId
from pyllmkit.domain.models import Model, ModelFamily, ModelId, ModelIdentity, ModelLimits
from pyllmkit.domain.providers import InferenceProvider, ProviderId
from pyllmkit.domain.registry import CapabilityResolver, LimitResolver, ResolutionReason
from pyllmkit.domain.registry.constraints import merge_constraints


CHAT = CapabilityId("chat")
TOOLS = CapabilityId("tool_calling")


def _support(level: SupportLevel | None, *constraints: CapabilityConstraint) -> CapabilitySupport:
    return CapabilitySupport(
        level, tuple(constraints), notes="partial conditions" if level is SupportLevel.PARTIAL else None
    )


def _caps(
    level: SupportLevel | None, *constraints: CapabilityConstraint, capability: CapabilityId = TOOLS
) -> CapabilitySet:
    return CapabilitySet((Capability(capability, _support(level, *constraints)),))


def _model(
    level: SupportLevel | None = SupportLevel.NATIVE,
    *,
    limits: ModelLimits | None = None,
    capabilities: CapabilitySet | None = None,
) -> Model:
    return Model(
        ModelId("m"), ModelIdentity(ModelFamily("llama")),
        limits=limits, capabilities=_caps(level) if capabilities is None else capabilities,
    )


def _deployment(
    level: SupportLevel | None = SupportLevel.NATIVE,
    *,
    local: bool = False,
    limits: ModelLimits | None = None,
    capabilities: CapabilitySet | None = None,
) -> Deployment:
    return Deployment(
        DeploymentId("d"), ModelId("m"),
        provider_id=None if local else ProviderId("p"),
        capabilities=_caps(level) if capabilities is None else capabilities,
        limits=limits,
    )


def _provider(
    level: SupportLevel | None = SupportLevel.NATIVE,
    *,
    limits: ModelLimits | None = None,
    capabilities: CapabilitySet | None = None,
) -> InferenceProvider:
    return InferenceProvider(
        ProviderId("p"), "Provider",
        capabilities=_caps(level) if capabilities is None else capabilities,
        limits=limits,
    )


def _one(
    model: Model, deployment: Deployment, provider: InferenceProvider | None = None
):
    result = CapabilityResolver().resolve(model, deployment, provider, (TOOLS,))
    item = result.get(TOOLS)
    assert item is not None
    return item


def test_ac025_all_native_sources_are_confirmed_and_deterministic() -> None:
    model, dep, provider = _model(), _deployment(), _provider()
    first = CapabilityResolver().resolve(model, dep, provider)
    second = CapabilityResolver().resolve(model, dep, provider)
    assert first == second
    item = first.get(TOOLS)
    assert item is not None
    assert first.capabilities.supports(TOOLS)
    assert first.capabilities.get(CHAT) is None
    assert item.fully_native and item.confirmed_usable
    assert item.reason is ResolutionReason.NATIVE
    assert tuple(e.source for e in item.evidence) == ("model", "deployment", "provider")
    assert tuple(e.state for e in item.evidence) == ("NATIVE", "NATIVE", "NATIVE")
    assert first.model_id == ModelId("m")
    assert first.deployment_id == DeploymentId("d")
    assert first.provider_id == ProviderId("p")


def test_ac026_unknown_deployment_remains_unknown_not_native() -> None:
    dep = _deployment(capabilities=CapabilitySet())
    item = _one(_model(), dep, _provider())
    assert item.level is None
    assert item.reason is ResolutionReason.UNKNOWN
    assert not item.confirmed_usable
    assert item.evidence[1].state == "UNKNOWN"


def test_ac026_missing_provider_snapshot_is_unknown_not_not_applicable() -> None:
    item = _one(_model(), _deployment())
    assert item.level is None
    assert item.evidence[2].state == "UNKNOWN"
    assert item.evidence[2].applicable
    assert not item.fully_native


def test_ac026_unknown_explicit_capability_and_unknown_model_default() -> None:
    item = _one(_model(level=None), _deployment(), _provider())
    assert item.level is None
    assert item.evidence[0].state == "UNKNOWN"
    unknown_model = _model(capabilities=CapabilitySet())
    assert _one(unknown_model, _deployment(), _provider()).level is None


def test_ac027_explicit_unsupported_vetoes_unknown() -> None:
    item = _one(_model(SupportLevel.UNSUPPORTED), _deployment(level=None), _provider())
    assert item.level is SupportLevel.UNSUPPORTED
    assert item.reason is ResolutionReason.UNSUPPORTED_VETO
    assert not item.confirmed_usable
    assert item.evidence[1].state == "UNKNOWN"


@pytest.mark.parametrize(
    ("levels", "expected", "reason", "emulated"),
    [
        ((SupportLevel.PARTIAL, SupportLevel.NATIVE, SupportLevel.NATIVE),
         SupportLevel.PARTIAL, ResolutionReason.PARTIAL, False),
        ((SupportLevel.EMULATED, SupportLevel.NATIVE, SupportLevel.NATIVE),
         SupportLevel.EMULATED, ResolutionReason.EMULATED, True),
        ((SupportLevel.PARTIAL, SupportLevel.EMULATED, SupportLevel.NATIVE),
         SupportLevel.PARTIAL, ResolutionReason.PARTIAL_EMULATED, True),
        ((SupportLevel.NATIVE, SupportLevel.EMULATED, SupportLevel.PARTIAL),
         SupportLevel.PARTIAL, ResolutionReason.PARTIAL_EMULATED, True),
    ],
)
def test_ac028_mixed_support_preserves_emulation(
    levels: tuple[SupportLevel, SupportLevel, SupportLevel],
    expected: SupportLevel,
    reason: ResolutionReason,
    emulated: bool,
) -> None:
    item = _one(_model(levels[0]), _deployment(levels[1]), _provider(levels[2]))
    assert item.level is expected
    assert item.reason is reason
    assert item.emulated is emulated


def test_ac029_local_provider_is_not_applicable_only_when_proven_absent() -> None:
    local = _deployment(local=True)
    item = _one(_model(), local)
    assert item.level is SupportLevel.NATIVE
    assert item.evidence[-1].state == "NOT_APPLICABLE"
    assert not item.evidence[-1].applicable


def test_ac029_incompatible_context_references_rejected() -> None:
    resolver = CapabilityResolver()
    with pytest.raises(DomainValidationError, match="ModelId"):
        resolver.resolve(_model(), Deployment(DeploymentId("d"), ModelId("wrong")))
    with pytest.raises(DomainValidationError, match="ProviderId"):
        resolver.resolve(
            _model(), _deployment(),
            InferenceProvider(ProviderId("wrong"), "Other"),
        )
    with pytest.raises(DomainValidationError, match="local"):
        resolver.resolve(_model(), _deployment(local=True), _provider())
    with pytest.raises(DomainValidationError):
        resolver.resolve(cast(Model, "model"), _deployment())
    with pytest.raises(DomainValidationError):
        resolver.resolve(_model(), cast(Deployment, "deployment"))
    with pytest.raises(DomainValidationError):
        resolver.resolve(_model(), _deployment(), cast(InferenceProvider, "provider"))


def test_ac030_requested_capabilities_are_canonical_and_reject_duplicate_ids() -> None:
    model = _model(capabilities=CapabilitySet((
        Capability(TOOLS, _support(SupportLevel.NATIVE)),
        Capability(CHAT, _support(SupportLevel.NATIVE)),
    )))
    dep = _deployment(capabilities=CapabilitySet((
        Capability(CHAT, _support(SupportLevel.NATIVE)),
        Capability(TOOLS, _support(SupportLevel.NATIVE)),
    )))
    provider = _provider(capabilities=dep.capabilities)
    report = CapabilityResolver().resolve(model, dep, provider, (TOOLS, CHAT))
    assert tuple(x.id for x in report.capabilities.items) == (CHAT, TOOLS)
    assert CapabilityResolver().resolve(model, dep, provider, ()).capabilities.items == ()
    for bad in ([TOOLS], (TOOLS, TOOLS), ("raw",)):
        with pytest.raises(DomainValidationError):
            CapabilityResolver().resolve(
                model, dep, provider, cast(tuple[CapabilityId, ...], bad),
            )
    with pytest.raises(DomainValidationError):
        report.capabilities.get(cast(CapabilityId, "raw"))
    with pytest.raises(FrozenInstanceError):
        report.capabilities.items = ()  # type: ignore[misc]


def test_ac030_union_contains_unknown_due_to_missing_applicable_layer() -> None:
    model = _model(capabilities=_caps(SupportLevel.NATIVE, capability=CHAT))
    dep = _deployment(capabilities=_caps(SupportLevel.NATIVE, capability=TOOLS))
    report = CapabilityResolver().resolve(model, dep, _provider())
    assert tuple(x.id.value for x in report.capabilities.items) == ("chat", "tool_calling")
    assert report.get(CHAT) is not None
    assert report.get(CHAT).level is None  # type: ignore[union-attr]
    assert not report.capabilities.supports(CHAT)


def test_ac031_limits_minimum_known_bound_keeps_unknown_provisional() -> None:
    model = _model(limits=ModelLimits(context_window=128000, max_output_tokens=16384))
    dep = _deployment(limits=ModelLimits(context_window=64000, max_output_tokens=4000))
    provider = _provider(limits=ModelLimits(context_window=32000))
    original = model.limits
    result = LimitResolver().resolve(model, dep, provider)
    assert result.limits.context_window == 32000
    assert result.limits.max_output_tokens == 4000
    assert result.get("context_window") is not None
    assert result.get("context_window").confirmed  # type: ignore[union-attr]
    assert result.get("max_output_tokens").provisional  # type: ignore[union-attr]
    assert "max_output_tokens" in result.provisional_fields
    assert "max_input_tokens" in result.unknown_fields
    assert model.limits is original
    assert dep.limits is not None and dep.limits.context_window == 64000


def test_ac031_unknown_limits_are_none_not_zero_and_local_has_two_sources() -> None:
    local = _deployment(local=True)
    result = LimitResolver().resolve(_model(), local)
    assert result.limits.context_window is None
    assert result.limits.max_tools is None
    assert "context_window" in result.unknown_fields
    assert result.get("context_window") is not None
    assert len(result.get("context_window").evidence) == 2  # type: ignore[union-attr]
    assert result.provisional_fields == ()


def test_ac031_true_zero_is_known_restrictive_bound() -> None:
    result = LimitResolver().resolve(
        _model(limits=ModelLimits(max_images=4)),
        _deployment(limits=ModelLimits(max_images=0)),
        _provider(limits=ModelLimits(max_images=3)),
    )
    assert result.limits.max_images == 0
    assert result.get("max_images").confirmed  # type: ignore[union-attr]
    assert result.get("missing") is None


def test_ac031_provider_metadata_not_supplied_makes_bound_provisional() -> None:
    result = LimitResolver().resolve(
        _model(limits=ModelLimits(context_window=32768)),
        _deployment(limits=ModelLimits(context_window=8192)),
    )
    assert result.limits.context_window == 8192
    assert "context_window" in result.provisional_fields
    assert result.get("context_window") is not None
    assert result.get("context_window").evidence[-1].value is None  # type: ignore[union-attr]
    with pytest.raises(DomainValidationError):
        LimitResolver().resolve(_model(), _deployment(local=True), _provider())


def test_ac032_restrictive_numeric_boolean_and_tuple_constraints() -> None:
    m = _caps(
        SupportLevel.NATIVE,
        CapabilityConstraint("max_tools", 128),
        CapabilityConstraint("min_tools", 1),
        CapabilityConstraint("parallel_tool_calls", True),
        CapabilityConstraint("supported_formats", ("json", "xml")),
    )
    d = _caps(
        SupportLevel.NATIVE,
        CapabilityConstraint("max_tools", 8),
        CapabilityConstraint("min_tools", 2),
        CapabilityConstraint("parallel_tool_calls", False),
        CapabilityConstraint("supported_formats", ("json",)),
    )
    p = _caps(SupportLevel.NATIVE)
    item = _one(_model(capabilities=m), _deployment(capabilities=d), _provider(capabilities=p))
    assert item.level is SupportLevel.NATIVE
    assert item.constraints.qualified
    assert item.constraints.get("max_tools").value == 8  # type: ignore[union-attr]
    assert item.constraints.get("min_tools").value == 2  # type: ignore[union-attr]
    assert item.constraints.get("parallel_tool_calls").value is False  # type: ignore[union-attr]
    assert item.constraints.get("supported_formats").value == ("json",)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("name", "values", "issue"),
    [
        ("max_tools", (3, "3"), "TYPE_MISMATCH"),
        ("max_tools", (True, 4), "TYPE_MISMATCH"),
        ("parallel_tool_calls", (1, False), "TYPE_MISMATCH"),
        ("supported_formats", (("json",), "json"), "TYPE_MISMATCH"),
        ("schema_dialect", ("draft-07", "draft-2020"), "EXACT_VALUE_CONFLICT"),
        ("unknown_constraint", (1, 1), "UNKNOWN_POLICY"),
        ("max_tools", (-1, 2), "NEGATIVE_BOUND"),
        ("supported_formats", (("json",), ("xml",)), "EMPTY_ALLOWED_SET"),
    ],
)
def test_ac032_constraint_conflicts_fail_closed(
    name: str,
    values: tuple[object, object],
    issue: str,
) -> None:
    m = _caps(SupportLevel.NATIVE, CapabilityConstraint(name, values[0]))
    d = _caps(SupportLevel.NATIVE, CapabilityConstraint(name, values[1]))
    item = _one(_model(capabilities=m), _deployment(capabilities=d), _provider())
    assert item.level is None
    assert item.reason is ResolutionReason.CONSTRAINT_CONFLICT
    entry = item.constraints.get(name)
    assert entry is not None and entry.issue == issue
    assert not item.constraints.qualified
    assert item.constraints.conflicts


def test_ac032_inverted_range_detected_without_correction() -> None:
    caps = _caps(
        SupportLevel.NATIVE,
        CapabilityConstraint("min_tools", 12),
        CapabilityConstraint("max_tools", 5),
    )
    item = _one(_model(capabilities=caps), _deployment(), _provider())
    assert item.level is None
    assert item.constraints.get("min_tools").issue == "INVERTED_RANGE"  # type: ignore[union-attr]
    assert item.constraints.get("max_tools").issue == "INVERTED_RANGE"  # type: ignore[union-attr]


def test_ac032_exact_value_and_numeric_float_are_supported_when_compatible() -> None:
    m = _caps(
        SupportLevel.NATIVE,
        CapabilityConstraint("schema_dialect", "v1"),
        CapabilityConstraint("max_temperature", 0.8),
        CapabilityConstraint("allow_parallel", True),
    )
    d = _caps(
        SupportLevel.NATIVE,
        CapabilityConstraint("schema_dialect", "v1"),
        CapabilityConstraint("max_temperature", 0.5),
        CapabilityConstraint("allow_parallel", False),
    )
    item = _one(_model(capabilities=m), _deployment(capabilities=d), _provider())
    assert item.level is SupportLevel.NATIVE
    assert item.constraints.get("schema_dialect").value == "v1"  # type: ignore[union-attr]
    assert item.constraints.get("max_temperature").value == 0.5  # type: ignore[union-attr]
    assert item.constraints.get("allow_parallel").value is False  # type: ignore[union-attr]


def test_ac032_constraint_resolution_is_order_independent() -> None:
    model = _support(SupportLevel.NATIVE, CapabilityConstraint("max_tools", 100))
    provider = _support(SupportLevel.NATIVE, CapabilityConstraint("max_tools", 32))
    left = merge_constraints((("provider", provider), ("model", model)))
    right = merge_constraints((("model", model), ("provider", provider)))
    assert left == right
    assert left.get("max_tools").value == 32  # type: ignore[union-attr]
    assert tuple(e.source for e in left.get("max_tools").evidence) == (  # type: ignore[union-attr]
        "model", "provider"
    )


def test_unsupported_veto_remains_even_when_constraint_policy_unknown() -> None:
    bad = _caps(SupportLevel.UNSUPPORTED, CapabilityConstraint("unrecognized", "x"))
    item = _one(_model(capabilities=bad), _deployment(level=None), _provider())
    assert item.level is SupportLevel.UNSUPPORTED
    assert item.reason is ResolutionReason.UNSUPPORTED_VETO
    assert item.constraints.conflicts


def test_model_and_existing_m1_intersection_semantics_unchanged() -> None:
    native = _caps(SupportLevel.NATIVE)
    partial = _caps(SupportLevel.PARTIAL)
    with pytest.raises(DomainValidationError, match="conflicting declaration"):
        native.intersection(partial)
    assert native.intersection(native) == native
    assert _one(_model(), _deployment(), _provider()).level is SupportLevel.NATIVE
