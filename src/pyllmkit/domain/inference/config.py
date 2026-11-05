"""Provider-neutral generation settings; explicit absence and strict types (ADR-016)."""

from dataclasses import dataclass
from math import isfinite

from pyllmkit.domain.errors import DomainValidationError


def _float_field(
    name: str, value: float | None, *, minimum: float | None = None,
    exclusive_minimum: bool = False, maximum: float | None = None,
) -> None:
    if value is None:
        return
    if type(value) is not float or not isfinite(value):
        raise DomainValidationError(f"{name} must be a finite float or None")
    if minimum is not None and (
        value <= minimum if exclusive_minimum else value < minimum
    ):
        raise DomainValidationError(f"{name} is outside the domain range")
    if maximum is not None and value > maximum:
        raise DomainValidationError(f"{name} is outside the domain range")


def _int_field(name: str, value: int | None, *, minimum: int | None = None) -> None:
    if value is None:
        return
    if type(value) is not int:
        raise DomainValidationError(f"{name} must be an exact int or None")
    if minimum is not None and value < minimum:
        raise DomainValidationError(f"{name} is outside the domain range")


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Pure immutable intent. None never means zero or provider default.

    Float fields require exact finite float values (0.0, not int 0).
    A present stop_sequences=() differs from stop_sequences=None.
    """

    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    seed: int | None = None
    stop_sequences: tuple[str, ...] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None

    def __post_init__(self) -> None:
        _float_field("temperature", self.temperature, minimum=0.0)
        _float_field("top_p", self.top_p, minimum=0.0, exclusive_minimum=True, maximum=1.0)
        _float_field("presence_penalty", self.presence_penalty)
        _float_field("frequency_penalty", self.frequency_penalty)
        _int_field("top_k", self.top_k, minimum=1)
        _int_field("max_output_tokens", self.max_output_tokens, minimum=1)
        _int_field("seed", self.seed)
        if self.stop_sequences is not None and (
            type(self.stop_sequences) is not tuple
            or any(type(item) is not str or not item for item in self.stop_sequences)
        ):
            raise DomainValidationError("stop_sequences must be a tuple of nonempty strings or None")
