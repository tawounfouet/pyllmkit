"""P4-AC-017..024: structured output formats and domain validation acceptance."""

from typing import cast

import pytest

from pyllmkit.domain.capabilities import CapabilitySupport, SupportLevel
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.structured_output import (
    JsonResponseFormat,
    SchemaResponseFormat,
    StructuredOutput,
    StructuredValidationResult,
    TextResponseFormat,
    evaluate_response_support,
    validate_response_support,
    validate_structured_output,
)
from pyllmkit.domain.tooling import ToolSchema, ValidationStatus


def schema_format(strict: bool | None = None) -> SchemaResponseFormat:
    return SchemaResponseFormat(ToolSchema({
        "type": "object",
        "properties": {"name": {"type": "string", "minLength": 1}},
        "required": ["name"], "additionalProperties": False,
    }), strict=strict)


def test_p4_ac017_text_response_does_not_require_json() -> None:
    text = validate_structured_output(
        StructuredOutput(TextResponseFormat(), raw="not JSON")
    )
    assert text.validation.status is ValidationStatus.VALID
    assert evaluate_response_support(TextResponseFormat()).is_compatible is True
    assert validate_structured_output(
        StructuredOutput(TextResponseFormat())
    ).validation.status is ValidationStatus.UNKNOWN


def test_p4_ac018_json_expected_is_not_same_as_validated_json() -> None:
    fmt = JsonResponseFormat()
    not_parsed = validate_structured_output(StructuredOutput(fmt, raw='{"ok":true}'))
    assert not_parsed.validation.status is ValidationStatus.UNKNOWN
    parsed = validate_structured_output(StructuredOutput(fmt, parsed={"ok": True}))
    assert parsed.validation.status is ValidationStatus.VALID


def test_p4_ac019_invalid_schema_rejected() -> None:
    with pytest.raises(DomainValidationError, match="unsupported keyword"):
        schema_format_bad = ToolSchema({"$ref": "https://example.test/schema"})
        SchemaResponseFormat(schema_format_bad)
    with pytest.raises(DomainValidationError, match="SchemaResponseFormat.schema"):
        SchemaResponseFormat(cast(ToolSchema, {}))


def test_p4_ac020_none_distinct_from_false_strictness() -> None:
    assert JsonResponseFormat().strict is None
    assert JsonResponseFormat(strict=False).strict is False
    assert schema_format().strict is None
    assert schema_format(False).strict is False
    with pytest.raises(DomainValidationError, match="strict"):
        JsonResponseFormat(strict=cast(bool, 0))


def test_p4_ac021_schema_conformity_actually_validated() -> None:
    result = validate_structured_output(
        StructuredOutput(schema_format(True), parsed={"name": "Paris"})
    )
    assert result.validation.status is ValidationStatus.VALID
    assert result.validation.code is None


def test_p4_ac022_invalid_or_unparsed_never_claims_validity() -> None:
    invalid = validate_structured_output(
        StructuredOutput(schema_format(), raw='{"name":12}', parsed={"name": 12})
    )
    assert invalid.validation.status is ValidationStatus.INVALID
    assert invalid.validation.code == "type_mismatch"
    unknown = validate_structured_output(
        StructuredOutput(schema_format(), raw='{"name":"Paris"}')
    )
    assert unknown.validation.status is ValidationStatus.UNKNOWN
    with pytest.raises(DomainValidationError, match="evidence"):
        StructuredValidationResult(ValidationStatus.VALID)


def test_p4_ac023_capability_known_unknown_not_promoted() -> None:
    fmt = schema_format()
    unknown = evaluate_response_support(fmt)
    assert unknown.level is None and unknown.is_compatible is None
    assert not unknown.is_confirmed_native
    assert validate_response_support(fmt, CapabilitySupport(SupportLevel.EMULATED)).is_compatible is None
    assert validate_response_support(fmt, CapabilitySupport(SupportLevel.NATIVE)).is_compatible is True
    with pytest.raises(DomainValidationError, match="unsupported"):
        validate_response_support(fmt, CapabilitySupport(SupportLevel.UNSUPPORTED))


def test_p4_ac024_raw_secret_is_not_leaked() -> None:
    secret = "PRIVATE_TOKEN_FOR_TEST"
    result = validate_structured_output(StructuredOutput(
        schema_format(), raw=secret, parsed={"name": "Paris"}
    ))
    assert secret not in repr(result)
    assert secret not in repr(result.validation)
    assert secret not in repr(result.response_format)
    assert result.raw == secret
