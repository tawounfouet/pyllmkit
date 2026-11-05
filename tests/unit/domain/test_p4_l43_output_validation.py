"""L4.3 negative validation and deep copy tests."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    TextResponseFormat,
    evaluate_response_support,
    validate_response_support,
    validate_structured_output,
)
from pyllmkit.domain.tooling import ToolSchema, ValidationStatus


def test_null_parsed_distinct_from_absent() -> None:
    fmt = JsonResponseFormat()
    absent = StructuredOutput(fmt)
    null = StructuredOutput(fmt, parsed=None)
    assert not absent.has_parsed and null.has_parsed
    assert absent.validation.status is ValidationStatus.UNKNOWN
    assert validate_structured_output(absent).validation.status is ValidationStatus.UNKNOWN
    assert validate_structured_output(null).validation.status is ValidationStatus.VALID


def test_immutable_value_and_separate_validation_snapshots() -> None:
    data: dict[str, object] = {"v": [1, 2]}
    initial = StructuredOutput(JsonResponseFormat(), parsed=data)
    cast(list[int], data["v"]).append(3)
    assert initial.parsed == {"v": [1, 2]}
    exported = cast(dict[str, object], initial.parsed)
    cast(list[int], exported["v"]).clear()
    assert initial.parsed == {"v": [1, 2]}
    valid = validate_structured_output(initial)
    assert initial.validation.status is ValidationStatus.UNKNOWN
    assert valid.validation.status is ValidationStatus.VALID
    with pytest.raises(FrozenInstanceError):
        valid.response_format = TextResponseFormat()  # type: ignore[misc]


def test_text_raw_empty_is_valid_without_json() -> None:
    out = validate_structured_output(StructuredOutput(TextResponseFormat(), raw=""))
    assert out.validation.status is ValidationStatus.VALID


@pytest.mark.parametrize("bad", [object(), float("nan"), float("inf")])
def test_invalid_json_value_rejected(bad: object) -> None:
    with pytest.raises(DomainValidationError):
        StructuredOutput(JsonResponseFormat(), parsed=bad)


def test_type_and_size_guards() -> None:
    with pytest.raises(DomainValidationError, match="response_format"):
        StructuredOutput(cast(JsonResponseFormat, "json"))
    with pytest.raises(DomainValidationError, match="raw"):
        StructuredOutput(JsonResponseFormat(), raw=cast(str, 42))
    with pytest.raises(DomainValidationError, match="raw exceeds"):
        StructuredOutput(JsonResponseFormat(), raw="x" * (1_048_576 + 1))
    with pytest.raises(DomainValidationError, match="expected"):
        validate_structured_output(cast(StructuredOutput, None))
    with pytest.raises(DomainValidationError, match="strict"):
        SchemaResponseFormat(ToolSchema({}), strict=cast(bool, 1))


def test_no_fake_provider_compatibility_or_unsupplied_support() -> None:
    fmt = SchemaResponseFormat(ToolSchema({"type": "object"}))
    partial = CapabilitySupport(SupportLevel.PARTIAL, notes="limited")
    report = validate_response_support(fmt, partial)
    assert report.level is SupportLevel.PARTIAL and report.is_compatible is None
    assert evaluate_response_support(None).is_compatible is True
    assert evaluate_response_support(TextResponseFormat(), CapabilitySupport()).level is None
    with pytest.raises(DomainValidationError, match="declared_support"):
        evaluate_response_support(fmt, cast(CapabilitySupport, "native"))
    with pytest.raises(DomainValidationError, match="response format"):
        evaluate_response_support(cast(JsonResponseFormat, object()))


def test_schema_failure_keeps_payload_hidden() -> None:
    secret = "HIGHLY_SENSITIVE_PROMPT_TEXT"
    fmt = SchemaResponseFormat(ToolSchema({"type": "object", "required": ["name"]}))
    invalid = validate_structured_output(StructuredOutput(fmt, raw=secret, parsed={}))
    assert invalid.validation.status is ValidationStatus.INVALID
    assert invalid.validation.code == "required_missing"
    assert secret not in repr(invalid)
    assert secret not in repr(invalid.validation)
