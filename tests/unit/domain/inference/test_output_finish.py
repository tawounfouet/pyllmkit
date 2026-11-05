"""ADR-017: immutable text output, normalized reason and native provenance."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain import DomainValidationError
from pyllmkit.domain.inference import FinishReason, FinishReasonCode, TextOutput


@pytest.mark.parametrize("text", ["", "Bonjour", "漢字", "👋", "line 1\nline 2", "\x00"])
def test_text_output_preserves_exact_unicode_and_empty_text(text: str) -> None:
    output = TextOutput(text)
    assert output.text == text
    assert output.kind == "text"
    assert output == TextOutput(text)
    assert hash(output) == hash(TextOutput(text))


@pytest.mark.parametrize("bad", [None, 0, True, b"txt", [], {}, 2.5])
def test_text_output_rejects_non_str(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="TextOutput.text"):
        TextOutput(cast(str, bad))


def test_text_output_is_immutable_and_repr_does_not_expose_text() -> None:
    output = TextOutput("private response")
    with pytest.raises(FrozenInstanceError):
        output.text = "changed"  # type: ignore[misc]
    assert "private response" not in repr(output)


@pytest.mark.parametrize("code", list(FinishReasonCode))
def test_all_seven_finish_reason_codes_are_value_objects(code: FinishReasonCode) -> None:
    value = FinishReason(code)
    assert value.code is code
    assert value.native_reason is None
    assert value == FinishReason(code)
    assert hash(value) == hash(FinishReason(code))


def test_unknown_preserves_native_value_without_stop_fallback() -> None:
    value = FinishReason(FinishReasonCode.UNKNOWN, "weird_vendor_stop")
    assert value.code is FinishReasonCode.UNKNOWN
    assert value.code is not FinishReasonCode.STOP
    assert value.native_reason == "weird_vendor_stop"
    assert value != FinishReason(FinishReasonCode.UNKNOWN, None)
    assert "weird_vendor_stop" not in repr(value)


@pytest.mark.parametrize("bad", ["stop", "unknown", None, True, 1, {}])
def test_reason_code_requires_enum_not_raw_string(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="FinishReason.code"):
        FinishReason(cast(FinishReasonCode, bad))


@pytest.mark.parametrize("bad", [7, False, [], {}, b"secret"])
def test_native_reason_has_strict_optional_type(bad: object) -> None:
    with pytest.raises(DomainValidationError, match="native_reason"):
        FinishReason(FinishReasonCode.UNKNOWN, cast(str, bad))


def test_empty_native_string_is_preserved_not_coerced_to_none() -> None:
    value = FinishReason(FinishReasonCode.UNKNOWN, "")
    assert value.native_reason == ""
    assert value != FinishReason(FinishReasonCode.UNKNOWN, None)


def test_finish_reason_is_immutable_and_independent_of_run_state() -> None:
    reason = FinishReason(FinishReasonCode.CANCELLED)
    assert not hasattr(reason, "state")
    with pytest.raises(FrozenInstanceError):
        reason.code = FinishReasonCode.STOP  # type: ignore[misc]
