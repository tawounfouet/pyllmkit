"""Pure normalized failure codes, not provider-native exceptions (ADR-019)."""

from dataclasses import dataclass, field
from re import fullmatch

from pyllmkit.domain.errors import DomainValidationError


def validate_reason_code(value: str, field_name: str) -> None:
    """Limit public codes to stable snake_case identifiers, never raw messages."""
    if type(value) is not str or fullmatch(r"[a-z][a-z0-9_]*", value) is None:
        raise DomainValidationError(f"{field_name} must be a normalized snake_case code")


@dataclass(frozen=True, slots=True)
class InferenceFailure:
    """A failure observation, not an exception, stack trace or provider payload."""

    code: str = field(repr=False)

    def __post_init__(self) -> None:
        validate_reason_code(self.code, "InferenceFailure.code")
