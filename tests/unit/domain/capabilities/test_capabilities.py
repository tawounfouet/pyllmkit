"""L1.2 capability semantics: unknown, partial, emulated, immutable collections."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityConstraint,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.errors import DomainValidationError


def cap(name: str, level: SupportLevel | None = None) -> Capability:
    return Capability(CapabilityId(name), CapabilitySupport(level))


@pytest.mark.parametrize("raw", ["", " ", "ToolCalling", "a-b", "image/vision", 14, None])
def test_capability_id_rejects_invalid_identifier(raw: object) -> None:
    with pytest.raises(DomainValidationError):
        CapabilityId(raw)  # type: ignore[arg-type]


def test_capability_id_extensible_and_immutable() -> None:
    custom = CapabilityId("future_capability_42")
    assert str(custom) == "future_capability_42"
    with pytest.raises(FrozenInstanceError):
        custom.value = "x"  # type: ignore[misc]


@pytest.mark.parametrize("level", list(SupportLevel))
def test_all_declared_support_levels(level: SupportLevel) -> None:
    descriptor = CapabilitySupport(level=level, notes="limited" if level is SupportLevel.PARTIAL else None)
    assert descriptor.known
    assert descriptor.available == (level is not SupportLevel.UNSUPPORTED)


def test_unknown_is_not_native_or_unsupported() -> None:
    level = CapabilitySupport()
    assert level.level is None
    assert not level.known and not level.available
    assert level != CapabilitySupport(SupportLevel.UNSUPPORTED)


def test_partial_must_explain_limit() -> None:
    with pytest.raises(DomainValidationError):
        CapabilitySupport(level=SupportLevel.PARTIAL)
    limited = CapabilitySupport(
        SupportLevel.PARTIAL,
        constraints=(CapabilityConstraint("max_tools", 1),),
    )
    assert limited.available and limited.constraints[0].value == 1


def test_emulated_is_explicit_and_not_native() -> None:
    emulated = CapabilitySupport(SupportLevel.EMULATED, notes="provided by wrapper")
    assert emulated.level is SupportLevel.EMULATED
    assert emulated.level is not SupportLevel.NATIVE


@pytest.mark.parametrize("bad", [inf, nan, "", (), ("ok", ""), ["bad"], object()])
def test_constraint_rejects_invalid_values(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        CapabilityConstraint("max_tools", bad)  # type: ignore[arg-type]


def test_constraints_distinguish_bool_int_float_and_tuple() -> None:
    assert CapabilityConstraint("parallel_calls", True).value is True
    assert CapabilityConstraint("max_tools", 128).value == 128
    assert CapabilityConstraint("temperature", 0.4).value == 0.4
    assert CapabilityConstraint("formats", ("json", "text")).value == ("json", "text")


def test_duplicate_constraint_names_rejected() -> None:
    with pytest.raises(DomainValidationError):
        CapabilitySupport(
            SupportLevel.NATIVE,
            (CapabilityConstraint("max_tools", 1), CapabilityConstraint("max_tools", 2)),
        )


def test_collection_immutable_and_canonical_order() -> None:
    a = cap("alpha", SupportLevel.NATIVE)
    b = cap("beta", SupportLevel.EMULATED)
    c = CapabilitySet((b, a))
    assert c.items == (a, b)
    with pytest.raises(FrozenInstanceError):
        c.items = ()  # type: ignore[misc]


def test_collection_rejects_duplicate_id() -> None:
    with pytest.raises(DomainValidationError):
        CapabilitySet((cap("vision"), cap("vision", SupportLevel.NATIVE)))


def test_missing_support_remains_unknown() -> None:
    c = CapabilitySet((cap("vision", SupportLevel.NATIVE),))
    assert c.supports(CapabilityId("vision"))
    assert not c.contains(CapabilityId("tool_calling"))
    assert not c.supports(CapabilityId("tool_calling"))
    assert c.support_of(CapabilityId("tool_calling")).level is None


def test_known_unsupported_is_distinct_from_unknown() -> None:
    c = CapabilitySet((cap("vision", SupportLevel.UNSUPPORTED),))
    assert c.contains(CapabilityId("vision"))
    assert c.support_of(CapabilityId("vision")).level is SupportLevel.UNSUPPORTED
    assert c.support_of(CapabilityId("tool_calling")).level is None


def test_union_intersection_difference_work_for_consistent_catalog() -> None:
    a = cap("vision", SupportLevel.NATIVE)
    b = cap("tool_calling", SupportLevel.EMULATED)
    first = CapabilitySet((a,))
    second = CapabilitySet((a, b))
    assert first.union(second) == second
    assert second.intersection(first) == first
    assert second.difference(first) == CapabilitySet((b,))
    assert len(second) == 2
    assert tuple(second) == second.items


def test_conflicting_declarations_are_not_silently_resolved() -> None:
    native = CapabilitySet((cap("vision", SupportLevel.NATIVE),))
    unavailable = CapabilitySet((cap("vision", SupportLevel.UNSUPPORTED),))
    with pytest.raises(DomainValidationError, match="conflicting"):
        native.union(unavailable)
    with pytest.raises(DomainValidationError, match="conflicting"):
        native.intersection(unavailable)


def test_collection_requires_typed_members() -> None:
    with pytest.raises(DomainValidationError):
        CapabilitySet([cap("vision")])  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError):
        CapabilitySet(("vision",))  # type: ignore[arg-type]
