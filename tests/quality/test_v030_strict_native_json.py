"""Adapter-level strict JSON decoding does not accept parser extensions.

Native provider JSON must be standard and unambiguous before any domain
projection. Error messages and exception chaining contain no native bodies.
"""

import pytest

from pyllmkit.adapters.inference.native_stream_mapping import decode_native_json
from pyllmkit.adapters.inference.strict_json import (
    decode_provider_json_object,
    matches_model_alias,
)
from pyllmkit.application.inference import InvocationPortError


@pytest.mark.parametrize(
    "native",
    [
        b'{"a":1,"a":2}',
        b'{"a":{"x":1,"x":2}}',
        b'{"a":[{"x":1,"x":2}]}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b'{"a":[1,NaN]}',
        b'{"a":',
        b'[1,2,3]',
        b'{"a":"\xff"}',
    ],
)
def test_native_json_rejects_duplicate_nonstandard_or_invalid_bytes(
    native: bytes,
) -> None:
    with pytest.raises(InvocationPortError) as caught:
        decode_provider_json_object(native)
    assert caught.value.code == "provider_protocol_error"
    assert str(caught.value) == "provider_protocol_error"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "invalid",
    [
        '{"n": NaN}',
        '{"n": Infinity}',
        '{"n": -Infinity}',
        '{"nested": {"n": 1, "n": 2}}',
    ],
)
def test_streaming_native_json_uses_same_strict_profile(invalid: str) -> None:
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_native_json(invalid)


def test_native_json_accepts_valid_nested_object_without_type_coercion() -> None:
    raw = b'{"a":0,"b":{"c":[true,false,null,1.5]}}'
    assert decode_provider_json_object(raw) == {
        "a": 0,
        "b": {"c": [True, False, None, 1.5]},
    }
    assert decode_provider_json_object(raw.decode()) == {
        "a": 0,
        "b": {"c": [True, False, None, 1.5]},
    }


@pytest.mark.parametrize("invalid_type", [None, 1, [], {}, True])
def test_invalid_root_types_are_sanitized(invalid_type: object) -> None:
    with pytest.raises(InvocationPortError, match="provider_protocol_error"):
        decode_provider_json_object(invalid_type)  # type: ignore[arg-type]


def test_matches_model_alias_branch_coverage() -> None:
    """Verify matches_model_alias branches for exact, snapshot, latest and mismatch cases."""
    # Non-string checks
    assert not matches_model_alias(123, "gpt-4o")
    assert not matches_model_alias("gpt-4o", None)  # type: ignore[arg-type]

    # Exact match
    assert matches_model_alias("gpt-4o", "gpt-4o")

    # Snapshot and tag suffixes
    assert matches_model_alias("gpt-4o-2024-08-06", "gpt-4o")
    assert matches_model_alias("gpt-4o-20240806", "gpt-4o")
    assert matches_model_alias("gpt-4o-1234", "gpt-4o")
    assert matches_model_alias("gpt-4o-latest", "gpt-4o")
    assert matches_model_alias("llama3:8b-instruct", "llama3")

    # Expected alias trimming -latest / :latest
    assert matches_model_alias("gpt-4o", "gpt-4o-latest")
    assert matches_model_alias("gpt-4o-2024-08-06", "gpt-4o-latest")
    assert matches_model_alias("llama3", "llama3:latest")
    assert matches_model_alias("llama3:8b", "llama3:latest")

    # Non matching prefix or invalid suffix
    assert not matches_model_alias("claude-3-opus", "gpt-4o")
    assert not matches_model_alias("claude-3-opus", "gpt-4o-latest")
    assert not matches_model_alias("gpt-4o-invalid-version-string", "gpt-4o")

