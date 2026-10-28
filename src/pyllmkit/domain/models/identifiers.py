"""Model catalog identifiers (ADR-001, MODEL-001/003)."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError


def require_nonblank(value: str, field: str) -> str:
    """Validate identifiers without silently rewriting a supplied canonical value."""
    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class ModelId:
    """Provider-independent logical model identifier."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelId")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ModelArtifactId:
    """Physical artifact identifier distinct from ModelId."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelArtifactId")

    def __str__(self) -> str:
        return self.value
