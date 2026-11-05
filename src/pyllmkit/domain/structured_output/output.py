"""Immutable observed structured output with explicit validation evidence.

Parsing JSON text, provider invocation and auto-repair remain out of scope.
"""

from dataclasses import dataclass, field
from pyllmkit.domain.errors import DomainValidationError
from pyllmkit.domain.tooling.json_values import FrozenJSON, freeze_json, thaw_json
from pyllmkit.domain.tooling.validation import ValidationStatus
from pyllmkit.domain.tooling.value_validation import check_p4_json_value

from .formats import (
    JsonResponseFormat,
    ResponseFormat,
    SchemaResponseFormat,
    TextResponseFormat,
)

_ABSENT = object()
_PROOF = object()


@dataclass(frozen=True, slots=True, init=False)
class StructuredValidationResult:
    """Immutable, payload-free proof of actual validation, not a caller assertion."""

    status: ValidationStatus
    code: str | None

    def __init__(
        self,
        status: ValidationStatus,
        code: str | None = None,
        *,
        _proof: object = None,
    ) -> None:
        if _proof is not _PROOF:
            raise DomainValidationError("validation evidence must come from the validator")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "code", code)


def _result(status: ValidationStatus, code: str | None = None) -> StructuredValidationResult:
    return StructuredValidationResult(status, code, _proof=_PROOF)


@dataclass(frozen=True, slots=True, init=False)
class StructuredOutput:
    """An observed payload; validation never inferred from construction.

    raw may include secrets and is omitted from repr. parsed is stored using a
    deeply immutable JSON tree. An explicitly parsed JSON null is not ABSENT.
    """

    response_format: ResponseFormat
    _raw: str | None = field(repr=False)
    _parsed: FrozenJSON = field(repr=False)
    _has_parsed: bool = field(repr=False)
    _validation: StructuredValidationResult = field(repr=False)

    def __init__(
        self,
        response_format: ResponseFormat,
        raw: str | None = None,
        parsed: object = _ABSENT,
    ) -> None:
        if type(response_format) not in (
            TextResponseFormat, JsonResponseFormat, SchemaResponseFormat
        ):
            raise DomainValidationError("StructuredOutput.response_format is invalid")
        if raw is not None and type(raw) is not str:
            raise DomainValidationError("StructuredOutput.raw must be str or None")
        if raw is not None and len(raw.encode("utf-8")) > 1_048_576:
            raise DomainValidationError("StructuredOutput.raw exceeds size limit")
        present = parsed is not _ABSENT
        frozen = freeze_json(parsed) if present else None
        object.__setattr__(self, "response_format", response_format)
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "_parsed", frozen)
        object.__setattr__(self, "_has_parsed", present)
        object.__setattr__(self, "_validation", _result(ValidationStatus.UNKNOWN, "not_validated"))

    @property
    def raw(self) -> str | None:
        return self._raw

    @property
    def has_parsed(self) -> bool:
        return self._has_parsed

    @property
    def parsed(self) -> object:
        """Return a new mutable JSON tree; inspect has_parsed for absent vs null."""
        return thaw_json(self._parsed) if self._has_parsed else None

    @property
    def validation(self) -> StructuredValidationResult:
        return self._validation

    def _validated(self, result: StructuredValidationResult) -> "StructuredOutput":
        """Return a fresh immutable snapshot with proof from domain validation."""
        if type(result) is not StructuredValidationResult:
            raise DomainValidationError("StructuredOutput requires validation evidence")
        clone = object.__new__(StructuredOutput)
        object.__setattr__(clone, "response_format", self.response_format)
        object.__setattr__(clone, "_raw", self._raw)
        object.__setattr__(clone, "_parsed", self._parsed)
        object.__setattr__(clone, "_has_parsed", self._has_parsed)
        object.__setattr__(clone, "_validation", result)
        return clone


def validate_structured_output(output: StructuredOutput) -> StructuredOutput:
    """Assess format against observed content without parsing raw or calling a model.

    For text, an observed raw string (including empty) is sufficient.
    For JSON, a pre-parsed JSON value is required; raw text is not parsed here.
    For schema, that value must also pass the approved P4-JSON-1 profile.
    """
    if type(output) is not StructuredOutput:
        raise DomainValidationError("expected a StructuredOutput")
    fmt = output.response_format
    if type(fmt) is TextResponseFormat:
        if output.raw is None:
            return output._validated(_result(ValidationStatus.UNKNOWN, "text_absent"))
        return output._validated(_result(ValidationStatus.VALID))
    if not output.has_parsed:
        return output._validated(_result(ValidationStatus.UNKNOWN, "parsed_absent"))
    if type(fmt) is JsonResponseFormat:
        return output._validated(_result(ValidationStatus.VALID))
    if type(fmt) is SchemaResponseFormat:
        problem = check_p4_json_value(output.parsed, fmt.schema)
        if problem is not None:
            return output._validated(_result(ValidationStatus.INVALID, problem))
        return output._validated(_result(ValidationStatus.VALID))
    raise DomainValidationError("unsupported response format")
