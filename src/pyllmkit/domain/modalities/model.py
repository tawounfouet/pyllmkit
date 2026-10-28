"""Extensible input/output modality value objects."""

from dataclasses import dataclass

from pyllmkit.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True, order=True)
class Modality:
    """Canonical lower-snake-case content modality (not a capability)."""

    value: str

    def __post_init__(self) -> None:
        value = self.value
        if (
            not isinstance(value, str)
            or not value
            or not value.isascii()
            or not value[0].islower()
            or not value[0].isalpha()
            or not all(c.islower() or c.isdigit() or c == "_" for c in value)
        ):
            raise DomainValidationError("Modality must use lower_snake_case")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ModalitySet:
    """Directional modalities; None means not declared, empty means explicitly empty.

    MOD-001: inputs and outputs have separate meaning. No implicit OCR/conversion.
    """

    input_modalities: frozenset[Modality] | None = None
    output_modalities: frozenset[Modality] | None = None

    def __post_init__(self) -> None:
        for field in ("input_modalities", "output_modalities"):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, frozenset)
                or any(not isinstance(x, Modality) for x in value)
            ):
                raise DomainValidationError(f"{field} must be frozenset[Modality] or None")

    def accepts_input(self, modality: Modality) -> bool | None:
        if not isinstance(modality, Modality):
            raise DomainValidationError("expected Modality")
        return (
            None if self.input_modalities is None else modality in self.input_modalities
        )

    def can_output(self, modality: Modality) -> bool | None:
        if not isinstance(modality, Modality):
            raise DomainValidationError("expected Modality")
        return (
            None if self.output_modalities is None else modality in self.output_modalities
        )
