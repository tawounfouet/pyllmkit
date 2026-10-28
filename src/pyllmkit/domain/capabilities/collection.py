"""Immutable collection of capability declarations (not an effective resolver)."""

from collections.abc import Iterator
from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .model import Capability, CapabilityId, CapabilitySupport


@dataclass(frozen=True, slots=True)
class CapabilitySet:
    """Canonical immutable Capability collection.

    Collection union/intersection are only defined for non-conflicting declarations.
    A disagreement across layers must go to a future explicit CapabilityResolver.
    """

    items: tuple[Capability, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.items, tuple) or any(
            not isinstance(item, Capability) for item in self.items
        ):
            raise DomainValidationError("CapabilitySet items must be tuple[Capability, ...]")
        ids = [x.id.value for x in self.items]
        if len(ids) != len(set(ids)):
            raise DomainValidationError("duplicate CapabilityId")
        object.__setattr__(self, "items", tuple(sorted(self.items, key=lambda x: x.id.value)))

    def get(self, capability_id: CapabilityId) -> Capability | None:
        if not isinstance(capability_id, CapabilityId):
            raise DomainValidationError("expected CapabilityId")
        return next((x for x in self.items if x.id == capability_id), None)

    def contains(self, capability_id: CapabilityId) -> bool:
        return self.get(capability_id) is not None

    def support_of(self, capability_id: CapabilityId) -> CapabilitySupport:
        """Return explicit UNKNOWN for an absent declaration."""
        found = self.get(capability_id)
        return found.support if found is not None else CapabilitySupport()

    def supports(self, capability_id: CapabilityId) -> bool:
        """True only when explicit support (native, emulated or partial) is known."""
        return self.support_of(capability_id).available

    def union(self, other: "CapabilitySet") -> "CapabilitySet":
        """Merge compatible declarations. Never guess which conflicting value wins."""
        if not isinstance(other, CapabilitySet):
            raise DomainValidationError("union expects CapabilitySet")
        result = {x.id: x for x in self.items}
        for incoming in other.items:
            current = result.get(incoming.id)
            if current is not None and current != incoming:
                raise DomainValidationError(f"conflicting declaration: {incoming.id}")
            result[incoming.id] = incoming
        return CapabilitySet(tuple(result.values()))

    def intersection(self, other: "CapabilitySet") -> "CapabilitySet":
        """Only identical overlapping declarations are safe to retain."""
        if not isinstance(other, CapabilitySet):
            raise DomainValidationError("intersection expects CapabilitySet")
        keep: list[Capability] = []
        for current in self.items:
            incoming = other.get(current.id)
            if incoming is not None:
                if current != incoming:
                    raise DomainValidationError(f"conflicting declaration: {current.id}")
                keep.append(current)
        return CapabilitySet(tuple(keep))

    def difference(self, other: "CapabilitySet") -> "CapabilitySet":
        """Remove entries by ID; not a difference of effective support levels."""
        if not isinstance(other, CapabilitySet):
            raise DomainValidationError("difference expects CapabilitySet")
        excluded = {x.id for x in other.items}
        return CapabilitySet(tuple(x for x in self.items if x.id not in excluded))

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[Capability]:
        return iter(self.items)
