"""Descriptive model identity is independent of provider endpoint aliases."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .descriptors import ModelFamily, ModelRevision, ModelVariant, ModelVersion
from .identifiers import require_nonblank


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Immutable description of the logical model (ADR-002)."""

    family: ModelFamily
    version: ModelVersion | None = None
    variant: ModelVariant | None = None
    revision: ModelRevision | None = None
    specialization: str | None = None
    developer: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.family, ModelFamily):
            raise DomainValidationError("family must be a ModelFamily")
        for field, kind in (
            ("version", ModelVersion),
            ("variant", ModelVariant),
            ("revision", ModelRevision),
        ):
            value = getattr(self, field)
            if value is not None and not isinstance(value, kind):
                raise DomainValidationError(f"{field} must be a {kind.__name__} or None")
        for field in ("specialization", "developer"):
            value = getattr(self, field)
            if value is not None:
                require_nonblank(value, field)
