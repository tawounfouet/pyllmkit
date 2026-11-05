"""Pure conservative capability-constraint reduction (ADR-044, P6 L6.4).

Constraint names must have an explicit reduction policy. Unknown policy,
conflicting exact values, invalid types and inverted bounds produce safe
diagnostics; no arbitrary last-writer-wins selection is permitted.
"""

from dataclasses import dataclass, field, replace
from typing import TypeAlias, cast

from pyllmkit.domain.capabilities import CapabilitySupport
from pyllmkit.domain.capabilities.model import ConstraintValue

LayerName: TypeAlias = str


@dataclass(frozen=True, slots=True)
class ConstraintEvidence:
    """Single declared constraint and its logical source."""

    source: LayerName
    name: str
    value: ConstraintValue = field(repr=False)


@dataclass(frozen=True, slots=True)
class ResolvedConstraint:
    """Conservative value or explicit unresolved state for one constraint."""

    name: str
    value: ConstraintValue | None = field(repr=False)
    evidence: tuple[ConstraintEvidence, ...] = field(repr=False)
    issue: str | None = None


@dataclass(frozen=True, slots=True)
class ConstraintReport:
    """An immutable, deterministic reduction with typed conflict reasons."""

    entries: tuple[ResolvedConstraint, ...]

    @property
    def conflicts(self) -> tuple[ResolvedConstraint, ...]:
        return tuple(item for item in self.entries if item.issue is not None)

    @property
    def qualified(self) -> bool:
        return not self.conflicts

    def get(self, name: str) -> ResolvedConstraint | None:
        return next((item for item in self.entries if item.name == name), None)


def _reduce(name: str, values: tuple[ConstraintValue, ...]) -> tuple[ConstraintValue | None, str | None]:
    """Only known policies can produce a usable value (bool is not numeric)."""
    if name.startswith(("max_", "min_")):
        if any(type(value) not in (int, float) for value in values):
            return None, "TYPE_MISMATCH"
        numbers = tuple(cast(int | float, value) for value in values)
        if any(number < 0 for number in numbers):
            return None, "NEGATIVE_BOUND"
        return (min(numbers) if name.startswith("max_") else max(numbers)), None
    if name == "parallel_tool_calls" or name.startswith(("allow_", "supports_")):
        if any(type(value) is not bool for value in values):
            return None, "TYPE_MISMATCH"
        return all(cast(bool, value) for value in values), None
    if name in ("supported_formats", "allowed_formats") or name.startswith("allowed_"):
        if any(type(value) is not tuple for value in values):
            return None, "TYPE_MISMATCH"
        options = tuple(cast(tuple[str, ...], value) for value in values)
        allowed = tuple(sorted(set(options[0]).intersection(*(set(x) for x in options[1:]))))
        if not allowed:
            return (), "EMPTY_ALLOWED_SET"
        return allowed, None
    if name in ("schema_dialect", "format_name"):
        if any(type(value) is not str for value in values):
            return None, "TYPE_MISMATCH"
        if any(value != values[0] for value in values[1:]):
            return None, "EXACT_VALUE_CONFLICT"
        return values[0], None
    return None, "UNKNOWN_POLICY"


def merge_constraints(
    declarations: tuple[tuple[LayerName, CapabilitySupport], ...],
) -> ConstraintReport:
    """Reduce documented constraints while preserving provenance and conflicts."""
    grouped: dict[str, list[ConstraintEvidence]] = {}
    for source, support in declarations:
        for constraint in support.constraints:
            grouped.setdefault(constraint.name, []).append(
                ConstraintEvidence(source, constraint.name, constraint.value)
            )
    resolved: dict[str, ResolvedConstraint] = {}
    for name in sorted(grouped):
        evidence = tuple(sorted(grouped[name], key=lambda item: item.source))
        value, issue = _reduce(name, tuple(item.value for item in evidence))
        resolved[name] = ResolvedConstraint(name, value, evidence, issue)
    for name in sorted(resolved):
        if not name.startswith("min_"):
            continue
        suffix = name[4:]
        max_name = "max_" + suffix
        lower = resolved[name]
        upper = resolved.get(max_name)
        if upper is None or lower.issue is not None or upper.issue is not None:
            continue
        low = cast(int | float, lower.value)
        high = cast(int | float, upper.value)
        if low > high:
            resolved[name] = replace(lower, value=None, issue="INVERTED_RANGE")
            resolved[max_name] = replace(upper, value=None, issue="INVERTED_RANGE")
    return ConstraintReport(tuple(resolved[key] for key in sorted(resolved)))
