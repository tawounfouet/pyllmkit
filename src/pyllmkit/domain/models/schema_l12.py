"""Validated JSON-compatible codecs for L1.2 capability/modality value objects."""

from collections.abc import Mapping
from typing import cast

from pyllmkit.domain.capabilities import (
    Capability,
    CapabilityConstraint,
    CapabilityId,
    CapabilitySet,
    CapabilitySupport,
    SupportLevel,
)
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality, ModalitySet


def _dict(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise DomainValidationError(f"{label} must be a mapping with string keys")
    return cast(Mapping[str, object], value)


def _keys(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    extras = set(value) - allowed
    if extras:
        raise DomainValidationError(f"unknown {label} keys: {sorted(extras)}")


def _string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise DomainValidationError(f"{label} must be string")
    return value


def _constraint_value(value: object) -> bool | int | float | str | tuple[str, ...]:
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return tuple(cast(list[str], value))
    raise DomainValidationError("invalid capability constraint value")


def capabilities_to_object(capabilities: CapabilitySet) -> list[dict[str, object]]:
    return [
        {
            "id": cap.id.value,
            "support": {
                "level": cap.support.level.value if cap.support.level is not None else None,
                "notes": cap.support.notes,
                "constraints": [
                    {
                        "name": constraint.name,
                        "value": (
                            list(constraint.value)
                            if isinstance(constraint.value, tuple)
                            else constraint.value
                        ),
                    }
                    for constraint in cap.support.constraints
                ],
            },
        }
        for cap in capabilities.items
    ]


def capabilities_from_object(value: object) -> CapabilitySet:
    if not isinstance(value, list):
        raise DomainValidationError("capabilities must be a list")
    capabilities: list[Capability] = []
    for raw_cap in value:
        cap = _dict(raw_cap, "capability")
        _keys(cap, {"id", "support"}, "capability")
        support = _dict(cap.get("support"), "capability support")
        _keys(support, {"level", "notes", "constraints"}, "capability support")
        raw_level = support.get("level")
        if raw_level is None:
            level = None
        else:
            try:
                level = SupportLevel(_string(raw_level, "level"))
            except ValueError as exc:
                raise DomainValidationError("invalid support level") from exc
        raw_constraints = support.get("constraints", [])
        if not isinstance(raw_constraints, list):
            raise DomainValidationError("constraints must be a list")
        constraints: list[CapabilityConstraint] = []
        for raw_constraint in raw_constraints:
            c = _dict(raw_constraint, "constraint")
            _keys(c, {"name", "value"}, "constraint")
            if "value" not in c:
                raise DomainValidationError("constraint.value is required")
            constraints.append(
                CapabilityConstraint(
                    name=_string(c.get("name"), "constraint.name"),
                    value=_constraint_value(c["value"]),
                )
            )
        notes = support.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise DomainValidationError("notes must be string or null")
        capabilities.append(
            Capability(
                id=CapabilityId(_string(cap.get("id"), "capability.id")),
                support=CapabilitySupport(
                    level=level,
                    notes=notes,
                    constraints=tuple(constraints),
                ),
            )
        )
    return CapabilitySet(tuple(capabilities))


def modalities_to_object(modalities: ModalitySet) -> dict[str, object]:
    return {
        "input_modalities": (
            sorted(x.value for x in modalities.input_modalities)
            if modalities.input_modalities is not None else None
        ),
        "output_modalities": (
            sorted(x.value for x in modalities.output_modalities)
            if modalities.output_modalities is not None else None
        ),
    }


def modalities_from_object(value: object) -> ModalitySet:
    if value is None:
        return ModalitySet()
    data = _dict(value, "modalities")
    _keys(data, {"input_modalities", "output_modalities"}, "modalities")

    def parse(name: str) -> frozenset[Modality] | None:
        raw = data.get(name)
        if raw is None:
            return None
        if not isinstance(raw, list):
            raise DomainValidationError(f"{name} must be a list or null")
        declared = [_string(item, name) for item in raw]
        if len(declared) != len(set(declared)):
            raise DomainValidationError(f"duplicate {name}")
        return frozenset(Modality(item) for item in declared)

    return ModalitySet(
        input_modalities=parse("input_modalities"),
        output_modalities=parse("output_modalities"),
    )
