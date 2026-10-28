"""L1.2 directional modality semantics (MOD-001 to MOD-005)."""

from dataclasses import FrozenInstanceError

import pytest

from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.modalities import Modality, ModalitySet


@pytest.mark.parametrize("raw", ["", "TEXT", "video/audio", "text-image", " ", None, 1])
def test_invalid_modality_rejected(raw: object) -> None:
    with pytest.raises(DomainValidationError):
        Modality(raw)  # type: ignore[arg-type]


def test_modality_taxonomy_is_extensible() -> None:
    assert Modality("custom_future_3").value == "custom_future_3"
    assert Modality("text") != Modality("image")
    with pytest.raises(FrozenInstanceError):
        m = Modality("text")
        m.value = "image"  # type: ignore[misc]


def test_input_and_output_do_not_mix() -> None:
    m = ModalitySet(
        input_modalities=frozenset({Modality("text"), Modality("image")}),
        output_modalities=frozenset({Modality("text")}),
    )
    assert m.accepts_input(Modality("image")) is True
    assert m.can_output(Modality("image")) is False
    assert m.can_output(Modality("text")) is True


def test_unspecified_direction_remains_unknown() -> None:
    m = ModalitySet()
    assert m.accepts_input(Modality("text")) is None
    assert m.can_output(Modality("text")) is None


def test_declared_empty_is_not_unknown() -> None:
    m = ModalitySet(input_modalities=frozenset(), output_modalities=None)
    assert m.accepts_input(Modality("image")) is False
    assert m.can_output(Modality("image")) is None


def test_modality_set_cannot_use_mutable_collection() -> None:
    with pytest.raises(DomainValidationError):
        ModalitySet(input_modalities={Modality("text")})  # type: ignore[arg-type]
    with pytest.raises(DomainValidationError):
        ModalitySet(output_modalities=frozenset({"text"}))  # type: ignore[arg-type]


def test_no_implicit_modality_emulation() -> None:
    m = ModalitySet(
        input_modalities=frozenset({Modality("text")}),
        output_modalities=frozenset({Modality("text")}),
    )
    assert m.accepts_input(Modality("image")) is False
