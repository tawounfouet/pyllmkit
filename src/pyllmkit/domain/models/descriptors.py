"""Immutable model descriptors with optional, non-fabricated metadata."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError

from .identifiers import require_nonblank


def _optional_nonblank(value: str | None, field: str) -> None:
    if value is not None:
        require_nonblank(value, field)


def _nonnegative(value: int | None, field: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise DomainValidationError(f"{field} must be a non-negative integer or None")


@dataclass(frozen=True, slots=True)
class ModelFamily:
    """Canonical family label, not the inference provider."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelFamily")


@dataclass(frozen=True, slots=True)
class ModelVersion:
    """Model generation/version; deliberately not constrained to SemVer."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelVersion")


@dataclass(frozen=True, slots=True)
class ModelVariant:
    """Model size, tier or specialization variant."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelVariant")


@dataclass(frozen=True, slots=True)
class ModelRevision:
    """Specific checkpoint or snapshot revision, distinct from ModelVersion."""

    value: str

    def __post_init__(self) -> None:
        require_nonblank(self.value, "ModelRevision")


@dataclass(frozen=True, slots=True)
class ModelArchitecture:
    """Documented architecture only; None means unknown, not zero."""

    architecture_type: str | None = None
    parameter_count: int | None = None
    layer_count: int | None = None
    hidden_size: int | None = None
    attention_type: str | None = None
    mixture_of_experts: bool | None = None

    def __post_init__(self) -> None:
        _optional_nonblank(self.architecture_type, "architecture_type")
        _optional_nonblank(self.attention_type, "attention_type")
        for field in ("parameter_count", "layer_count", "hidden_size"):
            _nonnegative(getattr(self, field), field)
        if self.mixture_of_experts is not None and not isinstance(
            self.mixture_of_experts, bool
        ):
            raise DomainValidationError("mixture_of_experts must be bool or None")


@dataclass(frozen=True, slots=True)
class ModelLimits:
    """Known intrinsic limits; absence is not silently coerced to 0."""

    context_window: int | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_images: int | None = None
    max_tool_calls: int | None = None
    max_tools: int | None = None

    def __post_init__(self) -> None:
        for field in (
            "context_window", "max_input_tokens", "max_output_tokens",
            "max_images", "max_tool_calls", "max_tools",
        ):
            _nonnegative(getattr(self, field), field)
