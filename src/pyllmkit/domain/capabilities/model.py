"""Provider-agnostic capabilities and their declared support.

L1.2 models intrinsic declarations only. Effective support across provider,
deployment and endpoint is a later domain service, never inferred here.
"""

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from pyllmkit.domain.errors import DomainValidationError


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise DomainValidationError(f"{label} must be a nonempty ASCII identifier")
    if not (value[0].islower() and value[0].isalpha()):
        raise DomainValidationError(f"{label} must start with a lowercase letter")
    if not all(c.islower() or c.isdigit() or c == "_" for c in value):
        raise DomainValidationError(f"{label} must use lower_snake_case")
    return value


@dataclass(frozen=True, slots=True, order=True)
class CapabilityId:
    """Extensible string-backed identifier, not a closed Enum."""

    value: str

    def __post_init__(self) -> None:
        _identifier(self.value, "CapabilityId")

    def __str__(self) -> str:
        return self.value


class SupportLevel(StrEnum):
    """Declared support. Unknown is represented by None, not a fictional level."""

    UNSUPPORTED = "unsupported"
    EMULATED = "emulated"
    PARTIAL = "partial"
    NATIVE = "native"


ConstraintValue = bool | int | float | str | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapabilityConstraint:
    """An explicitly typed constraint, e.g. max_tools=128."""

    name: str
    value: ConstraintValue

    def __post_init__(self) -> None:
        _identifier(self.name, "CapabilityConstraint.name")
        value = self.value
        if isinstance(value, float) and not isfinite(value):
            raise DomainValidationError("float constraint must be finite")
        if isinstance(value, (bool, int, float, str)):
            if isinstance(value, str) and not value.strip():
                raise DomainValidationError("string constraint cannot be blank")
            return
        if isinstance(value, tuple) and value and all(
            isinstance(x, str) and x.strip() for x in value
        ):
            return
        raise DomainValidationError("constraint must be bool/int/finite float/str/tuple[str, ...]")


@dataclass(frozen=True, slots=True)
class CapabilitySupport:
    """Support descriptor; None means UNKNOWN, never NATIVE.

    PARTIAL requires an explicit constraint or explanation.
    """

    level: SupportLevel | None = None
    constraints: tuple[CapabilityConstraint, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.level is not None and not isinstance(self.level, SupportLevel):
            raise DomainValidationError("level must be SupportLevel or None")
        if not isinstance(self.constraints, tuple) or any(
            not isinstance(x, CapabilityConstraint) for x in self.constraints
        ):
            raise DomainValidationError("constraints must be tuple[CapabilityConstraint, ...]")
        names = [x.name for x in self.constraints]
        if len(set(names)) != len(names):
            raise DomainValidationError("constraint names must be unique")
        if self.notes is not None and (
            not isinstance(self.notes, str) or not self.notes.strip()
        ):
            raise DomainValidationError("notes must be a nonempty string or None")
        if self.level is SupportLevel.PARTIAL and not (self.constraints or self.notes):
            raise DomainValidationError("PARTIAL requires constraints or explanatory notes")

    @property
    def known(self) -> bool:
        return self.level is not None

    @property
    def available(self) -> bool:
        return self.level in {SupportLevel.NATIVE, SupportLevel.EMULATED, SupportLevel.PARTIAL}


@dataclass(frozen=True, slots=True)
class Capability:
    """A capability descriptor with intrinsic declared support."""

    id: CapabilityId
    support: CapabilitySupport = CapabilitySupport()

    def __post_init__(self) -> None:
        if not isinstance(self.id, CapabilityId):
            raise DomainValidationError("id must be a CapabilityId")
        if not isinstance(self.support, CapabilitySupport):
            raise DomainValidationError("support must be CapabilitySupport")
