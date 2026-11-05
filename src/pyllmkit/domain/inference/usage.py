"""Usage observations are not pricing, costs or provider defaults (ADR-018)."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class Usage:
    """Partial observed token counts; None != zero, total is never derived."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_input_tokens: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "reasoning_tokens",
            "cached_input_tokens",
        ):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise DomainValidationError(f"Usage.{name} must be a nonnegative int or None")
