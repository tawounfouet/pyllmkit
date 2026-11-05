"""P4 L4.3: offline typed output validation, no provider, no auto-repair."""

from pyllmkit.domain.structured_output import (
    SchemaResponseFormat,
    StructuredOutput,
    validate_structured_output,
)
from pyllmkit.domain.tooling import ToolSchema, ValidationStatus


def main() -> None:
    fmt = SchemaResponseFormat(ToolSchema({
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
        "additionalProperties": False,
    }), strict=True)
    valid = validate_structured_output(StructuredOutput(
        fmt, raw='{"city":"Paris"}', parsed={"city": "Paris"},
    ))
    invalid = validate_structured_output(StructuredOutput(
        fmt, raw='{"city":123}', parsed={"city": 123},
    ))
    assert valid.validation.status is ValidationStatus.VALID
    assert invalid.validation.status is ValidationStatus.INVALID
    print("L4.3: VALID and INVALID structured output verified offline.")


if __name__ == "__main__":
    main()
