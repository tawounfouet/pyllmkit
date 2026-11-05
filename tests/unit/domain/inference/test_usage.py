"""ADR-018: partial, nonnegative observations without invented totals or costs."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.inference import Usage

FIELDS = (
    "input_tokens", "output_tokens", "total_tokens",
    "reasoning_tokens", "cached_input_tokens",
)


def test_missing_values_remain_none_not_zeros() -> None:
    item = Usage()
    assert tuple(getattr(item, field) for field in FIELDS) == (None,) * 5
    assert item != Usage(input_tokens=0)


@pytest.mark.parametrize("field", FIELDS)
def test_zero_is_valid_explicit_observation(field: str) -> None:
    item = Usage(**{field: 0})
    assert getattr(item, field) == 0
    assert all(getattr(item, name) is None for name in FIELDS if name != field)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("bad", [-1, True, False, 1.0, "1", [], {}, float("inf")])
def test_usage_rejects_invalid_count_types(field: str, bad: object) -> None:
    with pytest.raises(DomainValidationError, match=field):
        Usage(**{field: bad})  # type: ignore[arg-type]


def test_partial_report_does_not_infer_total_from_subcounts() -> None:
    usage = Usage(input_tokens=12, output_tokens=8, reasoning_tokens=3)
    assert usage.total_tokens is None
    assert usage.cached_input_tokens is None
    assert usage.output_tokens == 8


def test_source_total_is_preserved_even_if_not_sum_of_parts() -> None:
    usage = Usage(input_tokens=10, output_tokens=7, total_tokens=99)
    assert usage.total_tokens == 99
    assert usage.input_tokens + cast(int, usage.output_tokens) != usage.total_tokens


def test_distinct_usage_values_are_immutable_and_hashable() -> None:
    value = Usage(input_tokens=0, cached_input_tokens=3)
    assert value == Usage(input_tokens=0, cached_input_tokens=3)
    assert hash(value) == hash(Usage(input_tokens=0, cached_input_tokens=3))
    with pytest.raises(FrozenInstanceError):
        value.input_tokens = 99  # type: ignore[misc]


def test_no_pricing_cost_or_raw_provider_payload_in_usage_contract() -> None:
    item = Usage(input_tokens=10)
    for name in ("price", "pricing", "cost", "raw", "provider_metadata", "total_cost"):
        assert not hasattr(item, name)
    with pytest.raises(TypeError):
        Usage(cost=99)  # type: ignore[call-arg]
