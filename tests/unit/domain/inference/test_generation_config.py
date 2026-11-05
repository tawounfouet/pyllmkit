"""ADR-016: explicit absence, numeric boundaries and immutable stop sequences."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.inference import GenerationConfig


def test_all_unspecified_fields_are_none() -> None:
    config = GenerationConfig()
    assert (
        config.temperature,
        config.top_p,
        config.top_k,
        config.max_output_tokens,
        config.seed,
        config.stop_sequences,
        config.presence_penalty,
        config.frequency_penalty,
    ) == (None,) * 8


def test_valid_boundary_values_and_roundtrip_value_equality() -> None:
    config = GenerationConfig(
        temperature=0.0, top_p=1.0, top_k=1, max_output_tokens=1,
        seed=-1, stop_sequences=(), presence_penalty=-2.0, frequency_penalty=2.0,
    )
    assert config == GenerationConfig(
        temperature=0.0, top_p=1.0, top_k=1, max_output_tokens=1,
        seed=-1, stop_sequences=(), presence_penalty=-2.0, frequency_penalty=2.0,
    )
    assert hash(config) == hash(GenerationConfig(
        temperature=0.0, top_p=1.0, top_k=1, max_output_tokens=1,
        seed=-1, stop_sequences=(), presence_penalty=-2.0, frequency_penalty=2.0,
    ))
    assert config != GenerationConfig()
    assert config.stop_sequences == ()
    assert GenerationConfig(seed=0).seed == 0
    assert config.max_output_tokens == 1


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("temperature", float("nan")), ("temperature", float("inf")),
        ("temperature", float("-inf")), ("temperature", -0.01),
        ("temperature", 0), ("temperature", 1), ("temperature", True),
        ("temperature", "0.0"), ("top_p", 0.0), ("top_p", 1.001),
        ("top_p", 1), ("top_p", False), ("top_p", float("nan")),
        ("top_k", 0), ("top_k", -1), ("top_k", True), ("top_k", 2.0),
        ("max_output_tokens", 0), ("max_output_tokens", -1),
        ("max_output_tokens", True), ("max_output_tokens", 1.0),
        ("seed", 1.0), ("seed", True), ("seed", "1"),
        ("presence_penalty", 0), ("presence_penalty", float("inf")),
        ("frequency_penalty", 0), ("frequency_penalty", float("nan")),
    ],
)
def test_invalid_numbers_do_not_coerce(field: str, bad: object) -> None:
    with pytest.raises(DomainValidationError, match=field):
        GenerationConfig(**{field: bad})  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [["stop"], ("",), (None,), ("a", 1), "stop", True, 2])
def test_invalid_stop_sequences_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="stop_sequences"):
        GenerationConfig(stop_sequences=cast(tuple[str, ...], bad))


def test_order_and_duplicates_preserved_without_mutation() -> None:
    cfg = GenerationConfig(stop_sequences=("A", "B", "A"))
    assert cfg.stop_sequences == ("A", "B", "A")
    assert cfg != GenerationConfig(stop_sequences=None)
    with pytest.raises(FrozenInstanceError):
        cfg.stop_sequences = ("changed",)  # type: ignore[misc]
